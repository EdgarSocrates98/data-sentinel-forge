"""Join intelligence analyzer (§6.5-§6.10).

Every risk claim declares its evidence basis. Missing stats produce
missing-stats findings — never fabricated cardinalities.
"""

import hashlib
import re
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.analyzers.spark.joins.extractor import (
    JoinContext,
    extract_from_plan,
    extract_from_sql,
    load_stats,
)
from data_sentinel.analyzers.spark.joins.models import (
    CardinalityAssessment,
    JoinForm,
    JoinSignature,
    KeyStats,
    SkewKind,
    SkewSignal,
    UniquenessState,
)
from data_sentinel.analyzers.spark.plans.parser import parse_plan
from data_sentinel.core.contracts import (
    CapabilityManifest,
    DiagnosticRequest,
    Evidence,
    EvidenceProvenance,
    Finding,
    FindingCategory,
    FindingStatus,
    Severity,
    SourceType,
)
from data_sentinel.core.security import InputFile, sanitize_evidence_excerpt

_SUSPECTED_TOP_KEY_FRACTION = 0.10  # one declared key >10% of rows
_OBSERVED_SKEW_RATIO = 5.0  # p99/p50 task time
_TABLE_IDENT = re.compile(r"^[A-Za-z_][\w.]*$")


def _stats_step(table: str, *, columns: str | None = None) -> str:
    """ANALYZE TABLE only for real identifiers; derived sides get a generic step."""
    suffix = f" FOR COLUMNS {columns}" if columns else ""
    if _TABLE_IDENT.match(table) and table != "unknown":
        return f"ANALYZE TABLE {table} COMPUTE STATISTICS{suffix}"
    cols = f" nas colunas {columns}" if columns else ""
    return f"Coletar estatísticas de {table} (expressão/subquery){cols}"


class JoinIntelligenceAnalyzer(Analyzer):
    """Reasons about join cardinality risk from SQL/plan + declared stats."""

    @property
    def analyzer_id(self) -> str:
        return "join-intelligence-analyzer"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (
            SourceType.SQL_QUERY,
            SourceType.SPARK_PLAN,
            SourceType.PHYSICAL_PLAN,
            SourceType.METRICS,
            SourceType.CONFIG,
        )

    @property
    def supported_platforms(self) -> tuple[str, ...]:
        return ("spark", "aws_glue", "athena", "trino", "databricks", "generic")

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
            "Nunca deriva cardinalidade real a partir de contagens de linhas "
            "— estimativas exigem estatísticas de chave declaradas",
            "Skew de stage não identifica a chave desbalanceada — apenas "
            "sinaliza o estágio afetado",
            "Deduplicação nunca é sugerida automaticamente — altera semântica "
            "funcional e exige validação humana",
        )

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=list(self.supported_platforms),
            supported_runtimes=["spark-3.3", "spark-3.4", "spark-3.5", "trino"],
            required_permissions=["filesystem:read"],
            supported_operations=["analyze_joins"],
            limitations=list(self.limitations),
        )

    # ------------------------------------------------------------------

    def analyze(self, request: DiagnosticRequest, inputs: Sequence[InputFile]) -> AnalysisResult:
        started = time.monotonic()
        captured = datetime.now(UTC)
        self.validate_input(request, inputs)

        findings: list[Finding] = []
        evidence: list[Evidence] = []
        limitations: list[str] = list(self.limitations)
        ctx = JoinContext()
        runtime_metrics: dict[str, object] = {}

        dialect = "spark"
        if request.platform and str(request.platform) in ("athena", "trino"):
            dialect = "trino"

        for input_file in inputs:
            name = str(input_file.path)
            if name.endswith(".json"):
                tables, runtime, warns = load_stats(input_file.text)
                ctx.stats.update(tables)
                runtime_metrics.update(runtime)
                limitations.extend(f"{name}: {w}" for w in warns)
            elif name.endswith(".txt") or "plan" in name:
                plan = parse_plan(input_file.text, source=name)
                sub = extract_from_plan(plan)
                ctx.joins.extend(sub.joins)
                ctx.warnings.extend(sub.warnings)
            else:
                sub = extract_from_sql(input_file.text, dialect=dialect)
                ctx.joins.extend(sub.joins)
                ctx.warnings.extend(sub.warnings)

        digest = hashlib.sha256(
            "\n".join(i.text for i in inputs).encode()
        ).hexdigest()

        self._attach_stats(ctx)
        assessments = [self._assess(j) for j in ctx.joins]
        skews = self._skew_signals(ctx, runtime_metrics)

        def add_ev(location: str, excerpt: str, conf: float) -> str:
            ev = Evidence(
                source="join_analysis",
                source_location=location,
                captured_at=captured,
                content_hash=digest,
                sanitized_excerpt=sanitize_evidence_excerpt(excerpt, max_chars=500),
                provenance=EvidenceProvenance.DECLARED,
                confidence=conf,
            )
            evidence.append(ev)
            return ev.evidence_id

        for warn in ctx.warnings:
            limitations.append(warn)

        self._emit_join_findings(ctx, assessments, add_ev, findings)
        self._emit_skew_findings(skews, add_ev, findings)

        if not ctx.joins and not ctx.stats:
            findings.append(
                Finding(
                    category=FindingCategory.UNKNOWN,
                    severity=Severity.INFO,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        "Nenhum join nem estatística disponível para análise. "
                        "Forneça SQL, plano físico (EXPLAIN) e/ou descritor de "
                        "estatísticas JSON para investigação de cardinalidade."
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
            metadata={
                "joins": [
                    {
                        "join_id": j.join_id,
                        "form": str(j.form),
                        "left_table": j.left.table,
                        "right_table": j.right.table,
                        "equality_keys": j.equality_keys,
                        "is_inequality": j.is_inequality,
                        "is_expression_based": j.is_expression_based,
                        "source": j.source,
                    }
                    for j in ctx.joins
                ],
                "assessments": [
                    {
                        "join_id": a.join_id,
                        "estimated_output": a.estimated_output,
                        "estimate_basis": a.estimate_basis,
                        "fan_out": a.fan_out,
                        "many_to_many_risk": a.many_to_many_risk,
                        "expansion_ratio": a.expansion_ratio,
                        "missing_evidence": a.missing_evidence,
                        "stats_to_collect": a.stats_to_collect,
                    }
                    for a in assessments
                ],
                "skew": [
                    {"kind": str(s.kind), "target": s.target, "detail": s.detail}
                    for s in skews
                ],
            },
            duration_ms=int((time.monotonic() - started) * 1000),
            analyzed_at=captured,
        )

    # ------------------------------------------------------------------

    def _attach_stats(self, ctx: JoinContext) -> None:
        """Attach declared stats to join sides where names match."""
        for join in ctx.joins:
            for side in (join.left, join.right):
                stats = ctx.stats.get(side.table)
                if stats is None:
                    continue
                side.row_count = stats.row_count
                side.stats_source = stats.source
                key_stats: list[KeyStats] = [
                    k
                    for k in (stats.keys.get(kk.split(".")[-1]) for kk in side.keys)
                    if k is not None
                ]
                if not key_stats:
                    side.uniqueness = UniquenessState.UNKNOWN
                    continue
                if all(
                    k.distinct is not None
                    and side.row_count is not None
                    and k.distinct >= side.row_count
                    for k in key_stats
                ):
                    side.uniqueness = UniquenessState.KNOWN_UNIQUE
                elif any(
                    k.distinct is not None
                    and side.row_count is not None
                    and k.distinct < side.row_count
                    for k in key_stats
                ):
                    side.uniqueness = UniquenessState.KNOWN_NON_UNIQUE
                else:
                    side.uniqueness = UniquenessState.UNKNOWN

    def _assess(self, join: JoinSignature) -> CardinalityAssessment:
        missing: list[str] = []
        collect: list[str] = []

        for label, side in (("lado esquerdo", join.left), ("lado direito", join.right)):
            if side.row_count is None:
                missing.append(f"row_count do {label} ({side.table})")
                collect.append(_stats_step(side.table))
            if side.uniqueness == UniquenessState.UNKNOWN:
                missing.append(f"cardinalidade/unicidade das chaves do {label} ({side.table})")
                collect.append(
                    _stats_step(
                        side.table,
                        columns=", ".join(side.keys or ["<join_key>"]),
                    )
                )

        both = (join.left.uniqueness, join.right.uniqueness)
        m2m = (
            UniquenessState.KNOWN_NON_UNIQUE in both
            and join.left.uniqueness != UniquenessState.KNOWN_UNIQUE
            and join.right.uniqueness != UniquenessState.KNOWN_UNIQUE
        ) or (
            join.left.uniqueness == UniquenessState.UNKNOWN
            and join.right.uniqueness == UniquenessState.UNKNOWN
            and join.form not in (JoinForm.SEMI, JoinForm.ANTI)
            and bool(join.equality_keys)
        )

        estimated = "unavailable"
        basis = "unavailable"
        ratio = "unavailable"
        if (
            join.left.row_count is not None
            and join.right.row_count is not None
            and join.left.uniqueness == UniquenessState.KNOWN_UNIQUE
            and join.right.uniqueness == UniquenessState.KNOWN_NON_UNIQUE
            and join.form == JoinForm.INNER
        ):
            estimated = (
                f"~{join.right.row_count} linhas (estimado de "
                "estatísticas declaradas; não observado)"
            )
            basis = "estimated_from_declared"
            ratio = "1.0 (fan-out em N:1 sobre chave única)"

        fan_out = "unknown"
        if join.left.uniqueness == UniquenessState.KNOWN_UNIQUE and (
            join.right.uniqueness == UniquenessState.KNOWN_NON_UNIQUE
        ):
            fan_out = "none (N:1 ou 1:N sobre chave única declarada)"
        elif m2m:
            fan_out = "both"
        elif join.right.uniqueness == UniquenessState.KNOWN_NON_UNIQUE:
            fan_out = "right"
        elif join.left.uniqueness == UniquenessState.KNOWN_NON_UNIQUE:
            fan_out = "left"

        return CardinalityAssessment(
            join_id=join.join_id,
            estimated_output=estimated,
            estimate_basis=basis,
            fan_out=fan_out,
            many_to_many_risk=m2m,
            expansion_ratio=ratio,
            missing_evidence=missing,
            stats_to_collect=collect,
        )

    def _skew_signals(
        self, ctx: JoinContext, runtime: dict[str, object]
    ) -> list[SkewSignal]:
        signals: list[SkewSignal] = []

        # suspected — declared top-key concentration
        for name, table in ctx.stats.items():
            for tk in table.top_keys:
                frac = float(tk.get("fraction", 0) or 0)
                if frac >= _SUSPECTED_TOP_KEY_FRACTION:
                    signals.append(
                        SkewSignal(
                            kind=SkewKind.SUSPECTED,
                            target=name,
                            detail=(
                                f"chave declarada '{tk.get('key', '?')}' concentra "
                                f"{frac:.0%} das linhas (estatística declarada, "
                                "não observada em execução)"
                            ),
                            basis="declared top_keys fraction",
                        )
                    )

        # observed — runtime task-time skew per stage
        for stage, m in runtime.items():
            if not isinstance(m, dict):
                continue
            p50 = float(m.get("task_time_p50_ms", 0) or 0)
            p99 = float(m.get("task_time_p99_ms", 0) or 0)
            if p50 > 0 and p99 / p50 >= _OBSERVED_SKEW_RATIO:
                signals.append(
                    SkewSignal(
                        kind=SkewKind.OBSERVED,
                        target=str(stage),
                        detail=(
                            f"stage '{stage}': task p99/p50 = "
                            f"{p99 / p50:.1f}x ({p99:.0f}ms vs {p50:.0f}ms) "
                            "— skew observado em execução; a métrica de stage "
                            "não identifica a chave desbalanceada"
                        ),
                        basis="runtime task_time_p99/p50",
                    )
                )
        return signals

    # ------------------------------------------------------------------

    def _emit_join_findings(
        self,
        ctx: JoinContext,
        assessments: list[CardinalityAssessment],
        add_ev: Callable[[str, str, float], str],
        findings: list[Finding],
    ) -> None:
        by_id = {a.join_id: a for a in assessments}
        for join in ctx.joins:
            a = by_id[join.join_id]
            loc = (
                f"{join.source}:{join.source_span[0]}-{join.source_span[1]}"
                if join.source_span[0]
                else join.source
            )

            if join.form == JoinForm.CROSS:
                ev_id = add_ev(loc, f"cross join {join.condition or join.join_id}", 0.9)
                findings.append(
                    Finding(
                        category=FindingCategory.SQL_ANTIPATTERN,
                        severity=Severity.HIGH,
                        status=FindingStatus.CONFIRMED,
                        explanation=(
                            f"JOIN sem predicado de igualdade ({join.join_id}, "
                            f"{join.left.table} x {join.right.table}) — produto "
                            "cartesiano confirmado sintaticamente."
                        ),
                        evidence_ids=[ev_id],
                        recommendations=[
                            "Confirmar intenção; se legítimo, avaliar "
                            "broadcast do lado menor com materialização prévia"
                        ],
                        validation_steps=[
                            "Re-escrever com predicado e comparar cardinalidade "
                            "de saída em amostra controlada"
                        ],
                    )
                )

            if join.is_inequality:
                ev_id = add_ev(loc, f"inequality join {join.condition}", 0.8)
                findings.append(
                    Finding(
                        category=FindingCategory.COST,
                        severity=Severity.MEDIUM,
                        status=FindingStatus.CONFIRMED,
                        explanation=(
                            f"Join por desigualdade ({join.join_id}: "
                            f"'{join.condition[:80]}') — estatísticas de chave "
                            "não se aplicam; estimativas de cardinalidade "
                            "ficam indisponíveis por construção."
                        ),
                        evidence_ids=[ev_id],
                        validation_steps=[
                            "Medir saída real em amostra; considerar "
                            "range-partitioning ou bucketing quando aplicável"
                        ],
                    )
                )

            if a.many_to_many_risk:
                ev_id = add_ev(
                    loc,
                    f"many-to-many risk {join.left.table} ⋈ {join.right.table} "
                    f"unicidade={join.left.uniqueness}/{join.right.uniqueness}",
                    0.7,
                )
                findings.append(
                    Finding(
                        category=FindingCategory.DATA_SKEW,
                        severity=Severity.HIGH,
                        status=FindingStatus.POSSIBLE,
                        explanation=(
                            f"Risco de expansão many-to-many ({join.join_id}: "
                            f"{join.left.table} ⋈ {join.right.table}). "
                            "Quando ambos os lados podem ter múltiplas linhas "
                            "por chave, a saída é o produto das multiplicidades "
                            "por chave — crescimento intermediário pode exceder "
                            "as entradas em ordens de magnitude. "
                            + (
                                "Evidência: unicidade desconhecida nos dois lados."
                                if (
                                    join.left.uniqueness == UniquenessState.UNKNOWN
                                    and join.right.uniqueness == UniquenessState.UNKNOWN
                                )
                                else "Evidência: chaves declaradas não-únicas."
                            )
                        ),
                        evidence_ids=[ev_id],
                        alternatives=[
                            "Deduplicação NÃO é sugerida automaticamente: "
                            "remover duplicatas pode alterar resultados "
                            "funcionais (somas, contagens, semi-joins)"
                        ],
                        recommendations=[
                            "Coletar estatísticas de chave para confirmar "
                            "multiplicidade antes de agir",
                            "Se many-to-many for intencional, preparar "
                            "particionamento/memória para o volume intermediário",
                        ],
                        validation_steps=[
                            "SELECT k, COUNT(*) GROUP BY k HAVING COUNT(*)>1 "
                            "em cada lado para medir multiplicidade real",
                            *a.stats_to_collect,
                        ],
                    )
                )

            if a.missing_evidence:
                ev_id = add_ev(
                    loc,
                    f"missing stats {join.join_id}: {', '.join(a.missing_evidence)}",
                    0.8,
                )
                findings.append(
                    Finding(
                        category=FindingCategory.DATA_QUALITY,
                        severity=Severity.LOW,
                        status=FindingStatus.UNKNOWN,
                        explanation=(
                            f"Evidência insuficiente para estimar cardinalidade "
                            f"do join {join.join_id} ({join.left.table} ⋈ "
                            f"{join.right.table}). Faltam: "
                            + "; ".join(a.missing_evidence)
                            + ". Nenhuma cardinalidade é afirmada."
                        ),
                        evidence_ids=[ev_id],
                        validation_steps=a.stats_to_collect,
                    )
                )

    def _emit_skew_findings(
        self,
        skews: list[SkewSignal],
        add_ev: Callable[[str, str, float], str],
        findings: list[Finding],
    ) -> None:
        for s in skews:
            if s.kind == SkewKind.OBSERVED:
                ev_id = add_ev(f"runtime:{s.target}", s.detail, 0.9)
                findings.append(
                    Finding(
                        category=FindingCategory.DATA_SKEW,
                        severity=Severity.MEDIUM,
                        status=FindingStatus.CONFIRMED,
                        explanation=f"Skew OBSERVADO: {s.detail}",
                        evidence_ids=[ev_id],
                        recommendations=[
                            "Identificar a chave dominante via agregação "
                            "GROUP BY na entrada do estágio — a métrica de "
                            "stage não revela a chave",
                            "Avaliar AQE skew-split (spark.sql.adaptive.skewJoin)"
                            " ou salting como experimento controlado",
                        ],
                        validation_steps=[
                            "GROUP BY chave com COUNT(*) no input do stage "
                            "para localizar hot keys"
                        ],
                    )
                )
            else:
                ev_id = add_ev(f"stats:{s.target}", s.detail, 0.7)
                findings.append(
                    Finding(
                        category=FindingCategory.DATA_SKEW,
                        severity=Severity.LOW,
                        status=FindingStatus.POSSIBLE,
                        explanation=(
                            "Skew SUSPEITO (inferido de estatísticas "
                            f"declaradas): {s.detail}"
                        ),
                        evidence_ids=[ev_id],
                        recommendations=[
                            "Confirmar em execução real antes de aplicar "
                            "mitigações (salting muda a semântica das chaves)"
                        ],
                        validation_steps=[
                            "Executar amostra e medir distribuição de "
                            "task durations por partição"
                        ],
                    )
                )
