"""Spark execution plan analyzer (§5).

Investigation candidates per §5.5/§5.9 — presence of an Exchange or
SortMergeJoin is never treated as a problem on its own; findings are
contextual signals that require corroboration.
"""

import hashlib
import time
from collections.abc import Sequence
from datetime import UTC, datetime

from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.analyzers.spark.plans.models import ExecutionPlan, PlanNode
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

_MAX_NODES_FOR_ANALYSIS = 5_000
_SHUFFLE_MANY_EXCHANGES = 3
_REPARTITION_WARN = 2


class SparkPlanAnalyzer(Analyzer):
    """Parses EXPLAIN / physical plan text into a tree and flags candidates."""

    @property
    def analyzer_id(self) -> str:
        return "spark-plan-analyzer"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (
            SourceType.SPARK_PLAN,
            SourceType.PHYSICAL_PLAN,
            SourceType.OTHER,
        )

    @property
    def supported_platforms(self) -> tuple[str, ...]:
        return ("spark", "aws_glue", "databricks", "generic")

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
            "Plano estático — sem métricas de execução reais "
            "(bytes lidos, spill, skew) salvo quando o texto as declara",
            "Presença de Exchange/SortMergeJoin é sinal de investigação, "
            "não problema por si só",
            "Estatísticas exibidas são estimativas do otimizador salvo "
            "indicação explícita contrária",
        )

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=list(self.supported_platforms),
            supported_runtimes=["spark-3.3", "spark-3.4", "spark-3.5"],
            required_permissions=["filesystem:read"],
            supported_operations=["analyze_plan"],
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
        plan_meta: dict[str, object] = {"plans": []}

        for input_file in inputs:
            digest = hashlib.sha256(input_file.text.encode()).hexdigest()
            plan = parse_plan(input_file.text, source=str(input_file.path))
            self._check_depth(plan)

            if len(plan.nodes) > _MAX_NODES_FOR_ANALYSIS:
                limitations.append(
                    f"{input_file.path}: plano com {len(plan.nodes)} nós — "
                    "heurísticas executadas mas resultado pode estar truncado"
                )

            self._analyze_plan(plan, input_file, digest, captured, findings, evidence)

            for warning in plan.warnings:
                limitations.append(f"{input_file.path}: {warning}")
            if plan.aqe.get("isFinalPlan") == "false":
                limitations.append(
                    f"{input_file.path}: AdaptiveSparkPlan isFinalPlan=false — "
                    "plano inicial AQE; a execução final pode ter adaptado "
                    "joins/partições. Colete 'EXPLAIN' pós-execução ou "
                    "event log para o plano final."
                )

            plan_meta["plans"].append(  # type: ignore[attr-defined]
                {
                    "source": input_file.path,
                    "format": plan.format,
                    "spark_version": plan.spark_version,
                    "node_count": len(plan.nodes),
                    "operators": plan.operators(),
                    "roots": len(plan.roots),
                    "aqe": plan.aqe,
                    "shuffle_points": self._shuffle_points(plan),
                    "joins": self._join_nodes(plan),
                }
            )

        if not findings:
            findings.append(
                Finding(
                    category=FindingCategory.UNKNOWN,
                    severity=Severity.INFO,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        "Plano parseado sem candidatos de investigação "
                        "claros. Isso não significa que o plano é ótimo — "
                        "sem estatísticas reais de execução, "
                        "gargalos podem não ser visíveis no texto estático."
                    ),
                    evidence_ids=[],
                )
            )

        metadata = {**plan_meta}
        return AnalysisResult(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.version,
            request_id=request.request_id,
            findings=findings,
            evidence=evidence,
            limitations=limitations,
            metadata=metadata,
            duration_ms=int((time.monotonic() - started) * 1000),
            analyzed_at=captured,
        )

    # ------------------------------------------------------------------

    def _ev(
        self,
        plan: ExecutionPlan,
        node: PlanNode,
        file_path: str,
        digest: str,
        captured: datetime,
        confidence: float,
    ) -> Evidence:
        line_range = (
            f"{node.source_span[0]}"
            if node.source_span[0] == node.source_span[1]
            else f"{node.source_span[0]}-{node.source_span[1]}"
        )
        return Evidence(
            source="physical_plan",
            source_location=f"{file_path}:{line_range}",
            captured_at=captured,
            content_hash=digest,
            sanitized_excerpt=sanitize_evidence_excerpt(
                f"[{node.operator}] {node.raw_text}", max_chars=500
            ),
            provenance=EvidenceProvenance.OBSERVED,
            confidence=confidence,
        )

    def _check_depth(self, plan: ExecutionPlan) -> None:
        depth = 0
        stack: list[tuple[int, int]] = [(r, 0) for r in plan.roots]
        while stack:
            nid, d = stack.pop()
            depth = max(depth, d)
            stack.extend((c, d + 1) for c in plan.nodes[nid].children)
        if depth > 200:
            plan.warnings.append(f"árvore profunda ({depth} níveis) — renderização pode truncar")

    def _shuffle_points(self, plan: ExecutionPlan) -> list[int]:
        return [
            n.node_id
            for n in plan.nodes.values()
            if n.operator in ("Exchange", "BroadcastExchange")
        ]

    def _join_nodes(self, plan: ExecutionPlan) -> list[dict[str, object]]:
        out = []
        for n in plan.nodes.values():
            if "Join" in n.operator or n.operator == "CartesianProduct":
                out.append({"node_id": n.node_id, "operator": n.operator})
        return out

    def _analyze_plan(
        self,
        plan: ExecutionPlan,
        input_file: InputFile,
        digest: str,
        captured: datetime,
        findings: list[Finding],
        evidence: list[Evidence],
    ) -> None:
        counts = plan.operators()
        file_path = str(input_file.path)

        def add_ev(node: PlanNode, conf: float) -> str:
            ev = self._ev(plan, node, file_path, digest, captured, conf)
            evidence.append(ev)
            return ev.evidence_id

        # CartesianProduct — syntactic certainty it exists.
        for n in plan.nodes.values():
            if n.operator == "CartesianProduct":
                findings.append(
                    Finding(
                        category=FindingCategory.SQL_ANTIPATTERN,
                        severity=Severity.HIGH,
                        status=FindingStatus.CONFIRMED,
                        explanation=(
                            "CartesianProduct presente no plano físico "
                            f"(nó {n.node_id}) — join sem predicado gera "
                            "produto cartesiano completo. Raramente é a "
                            "forma pretendida."
                        ),
                        evidence_ids=[add_ev(n, 0.95)],
                        alternatives=[
                            "Verificar se o join carece de predicado ON",
                            "Se intencional, avaliar BroadcastNestedLoopJoin "
                            "com tabela pequena materializada",
                        ],
                        recommendations=[
                            "Inspecionar o SQL correspondente na linha de "
                            "origem e confirmar intenção do cross join"
                        ],
                        validation_steps=[
                            "Re-execução controlada em amostra com "
                            "predicado adicionado; comparar cardinalidade"
                        ],
                    )
                )

        # BroadcastNestedLoopJoin — exists; contextual risk.
        for n in plan.nodes.values():
            if n.operator == "BroadcastNestedLoopJoin":
                findings.append(
                    Finding(
                        category=FindingCategory.COST,
                        severity=Severity.MEDIUM,
                        status=FindingStatus.CONFIRMED,
                        explanation=(
                            "BroadcastNestedLoopJoin presente (nó "
                            f"{n.node_id}) — comparação O(n*m) em cada "
                            "partição. Aceitável para tabelas pequenas; "
                            "arriscado se o lado broadcast crescer."
                        ),
                        evidence_ids=[add_ev(n, 0.9)],
                        validation_steps=[
                            "Medir tamanho real do lado broadcast "
                            "(spark.sql.autoBroadcastJoinThreshold) e "
                            "número de linhas do lado streamed"
                        ],
                    )
                )

        # Many exchanges — shuffle candidates (never "wrong" per se).
        exchanges = [n for n in plan.nodes.values() if n.operator == "Exchange"]
        if len(exchanges) >= _SHUFFLE_MANY_EXCHANGES:
            ev_ids = [add_ev(n, 0.7) for n in exchanges[:3]]
            findings.append(
                Finding(
                    category=FindingCategory.COST,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.POSSIBLE,
                    explanation=(
                        f"{len(exchanges)} Exchange(s) de shuffle no plano. "
                        "Shuffle por si só não é defeito — investigue se "
                        "todos são necessários (joins múltiplos, agregações "
                        "em chaves diferentes, reparticionamento explícito)."
                    ),
                    evidence_ids=ev_ids,
                    recommendations=[
                        "Correlacionar cada Exchange com o operador "
                        "consumidor (join/aggregate) e validar se a chave "
                        "de particionamento é necessária"
                    ],
                    validation_steps=[
                        "Comparar com plano alternativo (broadcast no lado "
                        "menor, bucketing prévio, redução de "
                        "spark.sql.shuffle.partitions)"
                    ],
                )
            )

        # SortMergeJoin without statistics — risk signal only.
        for n in plan.nodes.values():
            if n.operator == "SortMergeJoin" and not n.statistics:
                findings.append(
                    Finding(
                        category=FindingCategory.COST,
                        severity=Severity.MEDIUM,
                        status=FindingStatus.POSSIBLE,
                        explanation=(
                            f"SortMergeJoin (nó {n.node_id}) sem "
                            "estatísticas declaradas no plano — o "
                            "otimizador pode ter escolhido shuffle+sort "
                            "sem cardinalidade confiável. Possível "
                            "candidato a broadcast se um lado for pequeno."
                        ),
                        evidence_ids=[add_ev(n, 0.7)],
                        validation_steps=[
                            "Coletar estatísticas das tabelas "
                            "(ANALYZE TABLE ... COMPUTE STATISTICS) e "
                            "re-gerar EXPLAIN",
                            "Medir bytes reais por lado via Spark UI",
                        ],
                    )
                )
                break  # one finding per plan for this class

        # Scans without filters — broad-scan candidates.
        for n in plan.nodes.values():
            if n.operator == "Scan" and (
                "DataFilters: []" in n.raw_text or "PushedFilters: []" in n.raw_text
            ):
                findings.append(
                    Finding(
                        category=FindingCategory.COST,
                        severity=Severity.LOW,
                        status=FindingStatus.POSSIBLE,
                        explanation=(
                            f"Scan (nó {n.node_id}) sem DataFilters "
                            "declarados — leitura ampla. Pode ser intencional; "
                            "se a query filtra em estágio posterior, "
                            "avaliar predicate pushdown/partition pruning."
                        ),
                        evidence_ids=[add_ev(n, 0.6)],
                        validation_steps=[
                            "Verificar partições lidas vs disponíveis no "
                            "Spark UI (input size/records)"
                        ],
                    )
                )
                break

        # Explicit Repartition beyond one — investigation candidate.
        if counts.get("Repartition", 0) >= _REPARTITION_WARN:
            nodes = [n for n in plan.nodes.values() if n.operator == "Repartition"]
            findings.append(
                Finding(
                    category=FindingCategory.COST,
                    severity=Severity.LOW,
                    status=FindingStatus.POSSIBLE,
                    explanation=(
                        f"{len(nodes)} Repartition(s) explícito(s) — cada "
                        "um força um shuffle completo. Verificar se o "
                        "particionamento requerido não já é satisfeito."
                    ),
                    evidence_ids=[add_ev(nodes[0], 0.6)],
                    validation_steps=[
                        "Comparar com plano sem repartition explícito e "
                        "medir shuffle read/write"
                    ],
                )
            )

        # AQE initial plan — hypothesis framing, not a problem.
        if plan.aqe.get("isFinalPlan") == "false":
            findings.append(
                Finding(
                    category=FindingCategory.CONFIGURATION,
                    severity=Severity.INFO,
                    status=FindingStatus.PROBABLE,
                    explanation=(
                        "Plano é AdaptiveSparkPlan inicial — otimizações "
                        "adaptativas (coalesce, skew split, join switch) "
                        "ainda não visíveis. Hipóteses sobre joins/shuffles "
                        "podem mudar no plano final."
                    ),
                    evidence_ids=[],
                    validation_steps=[
                        "Obter plano final via Spark UI ou event log para "
                        "comparação"
                    ],
                )
            )
