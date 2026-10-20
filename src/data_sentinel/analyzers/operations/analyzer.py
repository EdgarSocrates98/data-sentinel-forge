"""LakehouseOperationAnalyzer — MERGE/APPEND/incremental (§7, ds-0026).

Parses DML/DDL via sqlglot — NEVER executes SQL. Recognizes INSERT INTO /
OVERWRITE, MERGE, UPDATE, DELETE, CREATE, ALTER. Analyzes match keys,
matched/not-matched clauses, source-key duplication (declared stats or
observed data — never assumed), idempotency, and commit conflicts from
supplied logs. Never auto-deduplicates, never rewrites MERGE semantics.
"""

import hashlib
import json
import re
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

import sqlglot
from sqlglot import exp

from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.core.contracts.entities import (
    CapabilityManifest,
    DiagnosticRequest,
    Evidence,
    Finding,
)
from data_sentinel.core.contracts.enums import (
    EvidenceProvenance,
    FindingCategory,
    FindingStatus,
    Platform,
    Severity,
    SourceType,
)
from data_sentinel.core.security import InputFile
from data_sentinel.core.security.sanitize import sanitize_evidence_excerpt

_COMMIT_CONFLICT = re.compile(
    r"(ConcurrentModificationException|CommitFailedException|"
    r"optimistic.concurrency|commit conflict|version.*conflict)",
    re.IGNORECASE,
)
_DUP_HINT = re.compile(r"duplicate|duplicat", re.IGNORECASE)

_EvFn = Callable[..., Evidence]


class LakehouseOperationAnalyzer(Analyzer):
    @property
    def analyzer_id(self) -> str:
        return "lakehouse.operation"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def supported_platforms(self) -> tuple[str, ...]:
        return (Platform.SPARK, Platform.AWS_GLUE, Platform.ATHENA)

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (SourceType.SQL_QUERY,)

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
            "SQL é parseado, nunca executado — sem efeitos em dados",
            "Duplicação de chaves só é afirmada com estatística declarada "
            "ou unicidade observada; ausência de stats → risco, não fato",
            "Idempotência é analisada estaticamente — reprocessamento real "
            "depende de checkpointing/orquestração externa",
            "Nenhuma recomendação altera a semântica do MERGE declarado",
        )

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=list(self.supported_platforms),
            supported_runtimes=["spark-3.3", "spark-3.5", "glue-4.0", "glue-5.0", "glue-5.1"],
            required_permissions=["filesystem:read"],
            supported_operations=["analyze_lakehouse_operation"],
            limitations=list(self.limitations),
        )

    def analyze(self, request: DiagnosticRequest, inputs: Sequence[InputFile]) -> AnalysisResult:
        started = time.monotonic()
        captured = datetime.now(UTC)
        self.validate_input(request, inputs)

        findings: list[Finding] = []
        evidence: list[Evidence] = []
        limitations: list[str] = list(self.limitations)
        ops_meta: list[dict[str, object]] = []

        for input_file in inputs:
            digest = hashlib.sha256(input_file.text.encode()).hexdigest()

            def _ev(snippet: str, conf: float = 0.75,
                    _p: str = str(input_file.path), _d: str = digest) -> Evidence:
                ev = Evidence(
                    source="sql_operation",
                    source_location=_p,
                    captured_at=captured,
                    content_hash=_d,
                    sanitized_excerpt=sanitize_evidence_excerpt(snippet, max_chars=500),
                    provenance=EvidenceProvenance.DECLARED,
                    confidence=conf,
                )
                evidence.append(ev)
                return ev

            sql, stats, log = self._unwrap(input_file.text)
            self._log_conflicts(log, _ev, findings)
            try:
                trees = [t for t in sqlglot.parse(sql, dialect="spark") if t]
            except Exception as exc:  # parse failure → limitation
                limitations.append(f"{input_file.path}: SQL não parseado: {exc}")
                continue
            if not trees:
                limitations.append(f"{input_file.path}: nenhum statement SQL")
                continue
            for tree in trees:
                ops_meta.append({"operation": self._op_name(tree),
                                 "source": str(input_file.path)})
                self._dispatch(tree, sql, stats, _ev, findings, limitations)

        if not findings:
            findings.append(
                Finding(
                    category=FindingCategory.UNKNOWN,
                    severity=Severity.INFO,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        "Nenhum risco de operação lakehouse detectado — "
                        "sem stats/logs, duplicidade e conflitos não "
                        "podem ser descartados."
                    ),
                    evidence_ids=[],
                )
            )

        return AnalysisResult(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.version,
            request_id=request.request_id,
            findings=findings,
            evidence=evidence,
            limitations=limitations,
            metadata={"operations": ops_meta},
            duration_ms=int((time.monotonic() - started) * 1000),
            analyzed_at=captured,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _unwrap(text: str) -> tuple[str, dict[str, object], str]:
        """Accept bare SQL or envelope {sql, stats, log}."""
        stripped = text.lstrip()
        if not stripped.startswith("{"):
            return text, {}, ""
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return text, {}, ""
        if not isinstance(raw, dict) or "sql" not in raw:
            return text, {}, ""
        return (
            str(raw["sql"]),
            dict(raw["stats"]) if isinstance(raw.get("stats"), dict) else {},
            str(raw.get("log", "")),
        )

    @staticmethod
    def _op_name(tree: exp.Expr) -> str:
        if isinstance(tree, exp.Insert):
            return "insert_overwrite" if tree.args.get("overwrite") else "insert_into"
        return type(tree).__name__.lower()

    def _dispatch(
        self, tree: exp.Expr, sql: str, stats: dict[str, object],
        _ev: _EvFn, findings: list[Finding], limitations: list[str],
    ) -> None:
        if isinstance(tree, exp.Merge):
            self._merge(tree, stats, _ev, findings, limitations)
        elif isinstance(tree, exp.Insert):
            self._insert(tree, _ev, findings)
        elif isinstance(tree, (exp.Update, exp.Delete)):
            self._row_op(tree, _ev, findings)
        elif isinstance(tree, (exp.Create, exp.Alter)):
            self._ddl(tree, _ev, limitations)

    def _log_conflicts(
        self, log: str, _ev: _EvFn, findings: list[Finding],
    ) -> None:
        if not log:
            return
        hits = _COMMIT_CONFLICT.findall(log)
        if hits:
            ev = _ev(f"log declara conflito de commit: {sorted(set(hits))[:4]}")
            findings.append(
                Finding(
                    category=FindingCategory.DATA_QUALITY,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.CONFIRMED,
                    explanation=(
                        "Conflito de commit declarativo no log — concorrência "
                        "otimista do Iceberg falhou (outra escrita venceu). "
                        "Reexecução pode ser segura se a operação for idempotente."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Confirmar idempotência da operação antes de retry; "
                        "serializar escritores concorrentes na tabela."
                    ],
                )
            )

    def _merge(
        self, tree: exp.Merge, stats: dict[str, object],
        _ev: _EvFn, findings: list[Finding], limitations: list[str],
    ) -> None:
        on = tree.args.get("on") or tree.args.get("using_cond")
        whens = tree.args.get("whens") or tree.args.get("when")
        on_sql = on.sql(dialect="spark") if on else ""
        n_when = len(list(whens.find_all(exp.When))) if whens else 0
        ev = _ev(
            f"MERGE INTO {self._target(tree)} — ON: {on_sql[:120]}; "
            f"{n_when} cláusula(s) WHEN"
        )
        if not on:
            findings.append(
                Finding(
                    category=FindingCategory.DATA_QUALITY,
                    severity=Severity.HIGH,
                    status=FindingStatus.CONFIRMED,
                    explanation=(
                        "MERGE sem condição ON parseável — chave de match "
                        "indefinida; risco de match ambíguo ou cartesiano."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=["Declarar ON explícito com chaves de match."],
                )
            )
        elif " or " in on_sql.lower():
            findings.append(
                Finding(
                    category=FindingCategory.DATA_QUALITY,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.POSSIBLE,
                    explanation=(
                        "Condição ON com OR pode produzir matches ambíguos — "
                        "múltiplas linhas-fonte casando com o mesmo alvo."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Preferir ON conjuntivo por chave completa; "
                        "validar cardinalidade da fonte."
                    ],
                )
            )
        # source key duplication — only with declared stats
        dups = stats.get("source_duplicate_keys")
        unique_declared = stats.get("source_key_unique")
        if isinstance(dups, (int, float)) and dups > 0:
            ev2 = _ev(
                f"stats declaram {int(dups)} chaves-fonte duplicadas no "
                "merge source",
            )
            findings.append(
                Finding(
                    category=FindingCategory.DATA_QUALITY,
                    severity=Severity.HIGH,
                    status=FindingStatus.CONFIRMED,
                    explanation=(
                        f"{int(dups)} chaves duplicadas na fonte do MERGE — "
                        "Iceberg falha com ambiguity ou aplica update "
                        "imprevisível por linha."
                    ),
                    evidence_ids=[ev2.evidence_id],
                    recommendations=[
                        "Resolver duplicidade ANTES do merge (janela/dedup "
                        "determinística na fonte) — nunca deduplicar o alvo "
                        "automaticamente."
                    ],
                )
            )
        elif not unique_declared:
            findings.append(
                Finding(
                    category=FindingCategory.DATA_QUALITY,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        "Unicidade da chave-fonte do MERGE não declarada — "
                        "duplicidade não pode ser descartada nem afirmada."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Coletar contagem por chave no dataset-fonte antes "
                        "do merge (GROUP BY chave HAVING count>1)."
                    ],
                )
            )
        # matched-delete + not-matched-insert on non-unique key = ambiguity
        if whens and not unique_declared:
            limitations.append(
                "Sem estatística de unicidade, efeito de WHEN MATCHED/"
                "NOT MATCHED permanece hipotético."
            )

    def _insert(
        self, tree: exp.Insert, _ev: _EvFn, findings: list[Finding],
    ) -> None:
        overwrite = bool(tree.args.get("overwrite"))
        target = self._target(tree)
        if not overwrite:
            ev = _ev(f"INSERT INTO {target} — append")
            findings.append(
                Finding(
                    category=FindingCategory.DATA_QUALITY,
                    severity=Severity.LOW,
                    status=FindingStatus.POSSIBLE,
                    explanation=(
                        "APPEND sem deduplicação declarada — reprocessamento "
                        "duplica linhas se a fonte não tiver idempotência "
                        "garantida por chave/checkpoint externo."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Garantir idempotência upstream (chave de partição "
                        "por execução, checkpoint, ou dedup na fonte)."
                    ],
                )
            )
        else:
            _ev(f"INSERT OVERWRITE {target} — overwrite declarado")

    def _row_op(
        self, tree: exp.Expr, _ev: _EvFn, findings: list[Finding],
    ) -> None:
        where = tree.find(exp.Where)
        if where is None:
            ev = _ev(f"{self._op_name(tree).upper()} sem WHERE — full-table")
            findings.append(
                Finding(
                    category=FindingCategory.DATA_QUALITY,
                    severity=Severity.HIGH,
                    status=FindingStatus.CONFIRMED,
                    explanation=(
                        f"{self._op_name(tree).upper()} sem predicado afeta "
                        "a tabela inteira — copy-on-write de todos os arquivos."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=["Confirmar intenção; adicionar WHERE."],
                )
            )

    def _ddl(
        self, tree: exp.Expr, _ev: _EvFn, limitations: list[str],
    ) -> None:
        limitations.append(
            f"{self._op_name(tree).upper()} parseado mas não executado — "
            "impacto de DDL avaliado estaticamente apenas."
        )

    @staticmethod
    def _target(tree: exp.Expr) -> str:
        this = tree.args.get("this")
        if this is None:
            return "?"
        try:
            return str(this.sql(dialect="spark"))[:80]
        except Exception:
            return str(this)[:80]
