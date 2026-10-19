"""Static SQL analyzer via SQLGlot — Spark SQL + Trino/Presto (Athena).

Static analysis only: never executes, never infers physical plans (§02.5).
Status taxonomy: CONFIRMED only for syntactically certain antipattern
presence (cross/implicit join), POSSIBLE for heuristic hints.
"""

import hashlib
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import sqlglot
from sqlglot import exp

from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.core.contracts import (
    DiagnosticRequest,
    Evidence,
    EvidenceProvenance,
    Finding,
    FindingCategory,
    FindingStatus,
    Platform,
    Severity,
    SourceType,
)
from data_sentinel.core.security import InputFile, sanitize_evidence_excerpt

PLATFORM_DIALECTS: dict[Platform, str] = {
    Platform.SPARK: "spark",
    Platform.AWS_GLUE: "spark",
    Platform.DATABRICKS: "spark",
    Platform.TRINO: "trino",
    Platform.ATHENA: "trino",
    Platform.ICEBERG: "spark",
    Platform.GENERIC: "spark",
}

IN_LIST_THRESHOLD = 20


SqlHit = exp.Expr | str


@dataclass(frozen=True)
class SqlCheck:
    check_id: str
    severity: Severity
    status: FindingStatus
    title: str
    rationale: str
    suggestion: str
    detect: Callable[[exp.Expr, str], list[SqlHit]]


def _select_stars(tree: exp.Expr, _text: str) -> list[SqlHit]:
    return list(tree.find_all(exp.Star))


def _is_trivial_on(on: exp.Expr | None) -> bool:
    """True when ON is absent or a constant TRUE (sqlglot synthesizes on=TRUE
    for JOIN without predicate)."""
    if on is None:
        return True
    return isinstance(on, exp.Boolean) and on.this is True


def _predicateless_joins(tree: exp.Expr, _text: str) -> list[SqlHit]:
    hits: list[SqlHit] = []
    for join in tree.find_all(exp.Join):
        kind = str(join.args.get("kind") or "").upper()
        cross = kind == "CROSS"
        if cross or (not join.args.get("using") and _is_trivial_on(join.args.get("on"))):
            hits.append(join)
    return hits


_COMMA_FROM_RE = re.compile(
    r"\bFROM\s+[^\s,()]+\s+(?:AS\s+)?[A-Za-z_]\w*\s*,", re.IGNORECASE
)


def _implicit_joins(tree: exp.Expr, text: str) -> list[SqlHit]:
    """Comma-syntax joins: sqlglot normalizes them to CROSS joins, so the
    textual `FROM a, b` shape is detected on the raw text."""
    _ = tree
    return [m.group(0) for m in _COMMA_FROM_RE.finditer(text)]


def _nonsargable_predicates(tree: exp.Expr, _text: str) -> list[SqlHit]:
    hits: list[SqlHit] = []
    for where in tree.find_all(exp.Where):
        for func in where.find_all(exp.Func):
            if func.find(exp.Column) is not None:
                hits.append(func)
    return hits


def _order_without_limit(tree: exp.Expr, _text: str) -> list[SqlHit]:
    hits: list[SqlHit] = []
    for select in tree.find_all(exp.Select):
        if select.args.get("order") and not select.args.get("limit"):
            hits.append(select.args["order"])
    return hits


def _union_without_all(tree: exp.Expr, _text: str) -> list[SqlHit]:
    return [u for u in tree.find_all(exp.Union) if u.args.get("distinct", True)]


def _count_distinct(tree: exp.Expr, _text: str) -> list[SqlHit]:
    return [c for c in tree.find_all(exp.Count) if c.args.get("distinct")]


def _large_in_lists(tree: exp.Expr, _text: str) -> list[SqlHit]:
    return [
        i
        for i in tree.find_all(exp.In)
        if len(i.args.get("expressions") or []) >= IN_LIST_THRESHOLD
    ]


SQL_CHECKS: tuple[SqlCheck, ...] = (
    SqlCheck(
        "select-star",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "SELECT * / projeção ampla",
        "Projetar todas as colunas lê dados desnecessários e dificulta "
        "predicate/projection pushdown.",
        "Listar explicitamente as colunas necessárias.",
        _select_stars,
    ),
    SqlCheck(
        "join-without-predicate",
        Severity.HIGH,
        FindingStatus.CONFIRMED,
        "JOIN sem predicado (produto cartesiano)",
        "JOIN sem ON/USING ou CROSS JOIN gera produto cartesiano — "
        "presença sintaticamente certa; o impacto depende do plano.",
        "Adicionar predicado de junção ou confirmar intenção de CROSS JOIN.",
        _predicateless_joins,
    ),
    SqlCheck(
        "implicit-comma-join",
        Severity.MEDIUM,
        FindingStatus.POSSIBLE,
        "Join implícito com vírgula",
        "Sintaxe `FROM a, b` esconde a condição de junção e favorece "
        "produto cartesiano acidental.",
        "Reescrever com JOIN ... ON explícito.",
        _implicit_joins,
    ),
    SqlCheck(
        "non-sargable-predicate",
        Severity.MEDIUM,
        FindingStatus.POSSIBLE,
        "Predicado não-sargable (função envolvendo coluna)",
        "Função sobre coluna em WHERE impede uso de estatísticas/partição "
        "pelo otimizador.",
        "Mover a função para o lado literal ou materializar a coluna.",
        _nonsargable_predicates,
    ),
    SqlCheck(
        "order-by-without-limit",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "ORDER BY sem LIMIT",
        "Ordenação global completa é cara e raramente necessária sem limite.",
        "Avaliar LIMIT ou ordenar somente no consumidor.",
        _order_without_limit,
    ),
    SqlCheck(
        "union-without-all",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "UNION sem ALL",
        "UNION sem ALL executa deduplicação custosa; frequentemente o "
        "intencionado é UNION ALL.",
        "Confirmar necessidade de deduplicar ou usar UNION ALL.",
        _union_without_all,
    ),
    SqlCheck(
        "count-distinct",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "COUNT(DISTINCT)",
        "COUNT(DISTINCT) concentra dados em poucos reducers; em volumes "
        "grandes merece aproximação ou reescrita.",
        "Avaliar approx_count_distinct ou agregação em duas fases.",
        _count_distinct,
    ),
    SqlCheck(
        "large-in-list",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "Lista IN literal grande",
        f"IN (...) com ≥{IN_LIST_THRESHOLD} literais pode indicar filtro "
        "que deveria ser join com tabela de dimensão.",
        "Materializar valores em tabela e usar JOIN/semi-join.",
        _large_in_lists,
    ),
)


def _dialect_for(request: DiagnosticRequest) -> str:
    extra = (request.execution_context.extra if request.execution_context else {})
    return extra.get("sql_dialect") or PLATFORM_DIALECTS.get(request.platform, "spark")


def _line_of_fragment(source: str, fragment: str) -> int:
    needle = fragment.split("\n", 1)[0][:60]
    if not needle:
        return 1
    idx = source.find(needle)
    if idx < 0:
        return 1
    return source[:idx].count("\n") + 1


class SqlStaticAnalyzer(Analyzer):
    """Pattern-based static inspection of SQL text. No execution, no plan."""

    @property
    def analyzer_id(self) -> str:
        return "sql-static-analyzer"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (SourceType.SQL_QUERY,)

    @property
    def supported_platforms(self) -> tuple[str, ...]:
        return ("spark", "aws_glue", "trino", "athena", "generic")

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
            "Análise estática: não observa execução física nem custos reais",
            "Sem acesso a catálogo: não valida existência de tabelas/colunas",
            "Cobertura limitada à lista de antipadrões documentada",
        )

    def analyze(self, request: DiagnosticRequest, inputs: Sequence[InputFile]) -> AnalysisResult:
        self.validate_input(request, inputs)
        captured = datetime.now(UTC)
        dialect = _dialect_for(request)

        findings: list[Finding] = []
        evidence: list[Evidence] = []
        limitations: list[str] = [
            "Análise estática: não observa execução física (plano, métricas, "
            "estatísticas).",
        ]
        queries_meta: list[dict[str, object]] = []

        for input_file in inputs:
            digest = hashlib.sha256(input_file.text.encode()).hexdigest()
            try:
                tree = sqlglot.parse_one(input_file.text, read=dialect)
            except sqlglot.errors.ParseError as exc:
                limitations.append(
                    f"SQL não pôde ser analisado ({input_file.path}): {exc}"
                )
                findings.append(
                    Finding(
                        category=FindingCategory.UNKNOWN,
                        severity=Severity.INFO,
                        status=FindingStatus.UNKNOWN,
                        explanation=(
                            "Entrada SQL inválida para o dialeto "
                            f"'{dialect}': {exc}. Nenhuma análise de padrões "
                            "foi aplicada."
                        ),
                    )
                )
                continue

            if tree is None:
                limitations.append(f"SQL vazio ou sem statement: {input_file.path}")
                continue

            clauses = [
                name
                for cls, name in (
                    (exp.Group, "group_by"),
                    (exp.Order, "order_by"),
                    (exp.Limit, "limit"),
                    (exp.Having, "having"),
                    (exp.With, "cte"),
                )
                if tree.find(cls) is not None
            ]
            queries_meta.append(
                {
                    "file": str(input_file.path),
                    "tables": sorted({t.name for t in tree.find_all(exp.Table)}),
                    "join_count": len(list(tree.find_all(exp.Join))),
                    "cte_count": len(list(tree.find_all(exp.CTE))),
                    "subquery_count": len(list(tree.find_all(exp.Subquery))),
                    "clauses": clauses,
                }
            )

            for check in SQL_CHECKS:
                hits = check.detect(tree, input_file.text)
                if not hits:
                    continue
                ids: list[str] = []
                for hit in hits[:3]:
                    fragment = (
                        hit[:300]
                        if isinstance(hit, str)
                        else hit.sql(dialect=dialect)[:300]
                    )
                    ev = Evidence(
                        source="sql",
                        source_location=(
                            f"{input_file.path}:{_line_of_fragment(input_file.text, fragment)}"
                        ),
                        captured_at=captured,
                        content_hash=digest,
                        sanitized_excerpt=sanitize_evidence_excerpt(fragment, max_chars=400),
                        provenance=EvidenceProvenance.STATIC_INFERRED,
                        confidence=0.9 if check.status == FindingStatus.CONFIRMED else 0.55,
                    )
                    evidence.append(ev)
                    ids.append(ev.evidence_id)
                findings.append(
                    Finding(
                        category=FindingCategory.SQL_ANTIPATTERN,
                        severity=check.severity,
                        status=check.status,
                        explanation=(
                            f"{check.title}: {check.rationale} "
                            f"({len(hits)} ocorrência(s), dialeto {dialect})."
                        ),
                        evidence_ids=ids,
                        alternatives=[],
                        recommendations=[check.suggestion],
                        validation_steps=[
                            "Revisar a ocorrência indicada na evidência",
                            "Confirmar intenção antes de reescrever",
                        ],
                    )
                )

        return AnalysisResult(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.version,
            request_id=request.request_id,
            findings=findings,
            evidence=evidence,
            limitations=limitations,
            metadata={"dialect": dialect, "queries": queries_meta},
        )
