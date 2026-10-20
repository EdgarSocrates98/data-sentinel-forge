"""Spark configuration advisor (§8).

Never issues universal fixed recommendations: every suggestion declares
observed config, evidence, reasoning, experiment, labeled-hypothesis
benefit, risks, validation and rollback. Resource increases always
surface availability/cost implications.
"""

import hashlib
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.analyzers.spark.config.matrix import (
    CONFIG_MATRIX,
    support_status,
)
from data_sentinel.analyzers.spark.config.parser import (
    ConfigEntry,
    parse_config_text,
    parse_glue_arguments,
)
from data_sentinel.core.contracts import (
    CapabilityManifest,
    DiagnosticRequest,
    Evidence,
    EvidenceProvenance,
    Finding,
    FindingCategory,
    FindingStatus,
    OptimizationRecommendation,
    Severity,
    SourceType,
)
from data_sentinel.core.security import InputFile, sanitize_evidence_excerpt

_MEM_UNITS = {"k": 1, "m": 1024, "g": 1024**2, "t": 1024**3}


def _to_mb(value: str | None) -> float | None:
    if not value:
        return None
    v = value.strip().lower().rstrip("b")
    unit = v[-1] if v[-1] in _MEM_UNITS else "k"
    try:
        return float(v[:-1]) * _MEM_UNITS[unit] / 1024 if unit != "k" else float(v) / 1024
    except ValueError:
        return None


class SparkConfigAdvisor(Analyzer):
    """Evaluates spark.* configs against runtime compat + workload signals."""

    @property
    def analyzer_id(self) -> str:
        return "spark-config-advisor"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (SourceType.CONFIG, SourceType.GLUE_JOB, SourceType.OTHER)

    @property
    def supported_platforms(self) -> tuple[str, ...]:
        return ("spark", "aws_glue", "databricks", "generic")

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
            "Recomendações são hipóteses rotuladas — benefício esperado "
            "não é medido",
            "Sem métricas de workload, severidade de configs inadequadas "
            "permanece POSSIBLE",
            "Aumentos de recurso sempre indicam implicação de custo/quota",
        )

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=list(self.supported_platforms),
            supported_runtimes=["spark-3.3", "spark-3.4", "spark-3.5", "glue-4.0", "glue-5.0"],
            required_permissions=["filesystem:read"],
            supported_operations=["advise_config"],
            limitations=list(self.limitations),
        )

    # ------------------------------------------------------------------

    def analyze(self, request: DiagnosticRequest, inputs: Sequence[InputFile]) -> AnalysisResult:
        started = time.monotonic()
        captured = datetime.now(UTC)
        self.validate_input(request, inputs)

        entries: list[ConfigEntry] = []
        limitations: list[str] = list(self.limitations)
        for input_file in inputs:
            name = str(input_file.path)
            text = input_file.text
            if name.endswith(".json") or text.lstrip().startswith("{"):
                got = parse_glue_arguments(text)
                entries.extend(got or parse_config_text(text))
            else:
                entries.extend(parse_config_text(text, filename=name))

        configs = {e.key: e for e in entries}
        spark_v, glue_v = self._runtime(request, configs)

        findings: list[Finding] = []
        evidence: list[Evidence] = []
        recommendations: list[OptimizationRecommendation] = []
        digest = hashlib.sha256(
            "\n".join(i.text for i in inputs).encode()
        ).hexdigest()

        def ev(location: str, excerpt: str, conf: float) -> str:
            e = Evidence(
                source="config",
                source_location=location,
                captured_at=captured,
                content_hash=digest,
                sanitized_excerpt=sanitize_evidence_excerpt(excerpt, max_chars=400),
                provenance=EvidenceProvenance.DECLARED,
                confidence=conf,
            )
            evidence.append(e)
            return e.evidence_id

        # runtime-compat audit — incompatible configs flagged, non-applicable skipped
        compat_report: dict[str, str] = {}
        for key in sorted(set(configs) | set(CONFIG_MATRIX)):
            status, note = support_status(key, spark_v, glue_v)
            compat_report[key] = status
            if status == "unsupported" and key in configs:
                ev_id = ev(
                    key,
                    f"{key}={configs[key].value} — {note}",
                    0.85,
                )
                findings.append(
                    Finding(
                        category=FindingCategory.CONFIGURATION,
                        severity=Severity.MEDIUM,
                        status=FindingStatus.CONFIRMED,
                        explanation=(
                            f"Config incompatível com o runtime: {key}="
                            f"{configs[key].value} ({note})."
                        ),
                        evidence_ids=[ev_id],
                        recommendations=[
                            "Remover ou substituir pela config equivalente "
                            "do runtime declarado",
                            "Checklist: validar comportamento do job sem a "
                            "config antes de aplicar substituto",
                        ],
                        validation_steps=["Re-executar job em ambiente de teste"],
                    )
                )

        ctx = request.execution_context
        prior = (ctx.extra if ctx else {}) or {}
        workload = {
            "oom_evidence": prior.get("workload_oom_evidence") == "true",
            "stats_available": prior.get("workload_stats_available") == "true",
        }

        self._evaluate(configs, spark_v, glue_v, workload, ev, findings, recommendations)

        if not configs:
            findings.append(
                Finding(
                    category=FindingCategory.UNKNOWN,
                    severity=Severity.INFO,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        "Nenhuma configuração spark.* identificada nos "
                        "artefatos — sem config declarada, avaliação de "
                        "adequação fica indisponível (sem suposições)."
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
                "runtime": {"spark": spark_v, "glue": glue_v},
                "configs": {
                    k: {"value": e.value, "provenance": e.provenance}
                    for k, e in configs.items()
                },
                "compat": compat_report,
                "recommendations": [r.model_dump(mode="json") for r in recommendations],
            },
            duration_ms=int((time.monotonic() - started) * 1000),
            analyzed_at=captured,
        )

    # ------------------------------------------------------------------

    def _runtime(
        self, request: DiagnosticRequest, configs: dict[str, ConfigEntry]
    ) -> tuple[str | None, str | None]:
        ctx = request.execution_context
        extra = (ctx.extra if ctx else {}) or {}
        spark_v = extra.get("spark_version") or request.runtime_version
        glue_v = extra.get("glue_version")
        if glue_v and not spark_v:
            spark_v = {"3.0": "3.1", "4.0": "3.3", "5.0": "3.5"}.get(glue_v)
        return spark_v, glue_v

    def _rec(
        self,
        rec_id: str,
        target: str,
        observed: str,
        rationale: str,
        experiment: str,
        benefit: str,
        risks: str,
        validation: str,
        rollback: str,
        ev_ids: list[str],
    ) -> OptimizationRecommendation:
        return OptimizationRecommendation(
            recommendation_id=rec_id,
            target=target,
            proposed_change=experiment,
            rationale=(
                f"[config observada: {observed}] {rationale} "
                f"Benefício esperado (hipótese): {benefit}. Riscos: {risks}."
            ),
            expected_effect=f"hipótese: {benefit}",
            estimated_risk=risks,
            validation_plan=validation,
            rollback_plan=rollback,
            evidence_ids=ev_ids,
        )

    def _evaluate(
        self,
        configs: dict[str, ConfigEntry],
        spark_v: str | None,
        glue_v: str | None,
        workload: dict[str, bool],
        ev: Callable[[str, str, float], str],
        findings: list[Finding],
        recommendations: list[OptimizationRecommendation],
    ) -> None:
        runtime_desc = (
            f"Spark {spark_v}" if spark_v else "runtime não declarado"
        ) + (f" / Glue {glue_v}" if glue_v else "")

        aqe = configs.get("spark.sql.adaptive.enabled")
        aqe_on = aqe is None or aqe.value.lower() == "true"

        # AQE disabled
        if aqe is not None and not aqe_on:
            status, note = support_status("spark.sql.adaptive.enabled", spark_v, glue_v)
            if status in ("supported", "conditional"):
                ev_id = ev("spark.sql.adaptive.enabled", f"={aqe.value} ({note})", 0.8)
                findings.append(
                    Finding(
                        category=FindingCategory.CONFIGURATION,
                        severity=Severity.MEDIUM,
                        status=FindingStatus.POSSIBLE,
                        explanation=(
                            "AQE desabilitado explicitamente em runtime que "
                            f"o suporta ({runtime_desc}). AQE poderia "
                            "coalescer partições, trocar join strategy e "
                            "mitigar skew — a desabilitação pode ser "
                            "intencional (previsibilidade) ou legada."
                        ),
                        evidence_ids=[ev_id],
                        validation_steps=[
                            "Executar job de teste com AQE ativo e comparar "
                            "métricas de stage"
                        ],
                    )
                )
                recommendations.append(
                    self._rec(
                        "rec-aqe-enable",
                        "spark.sql.adaptive.enabled",
                        aqe.value,
                        "Habilitar AQE em runtime que o suporta.",
                        "Rodar job representativo com adaptive.enabled=true",
                        "coalescência de partições e join adaptativo podem "
                        "reduzir shuffle",
                        "mudança de plano pode alterar cardinalidade "
                        "intermediária; validar em ambiente não-produtivo",
                        "Comparar shuffle bytes e duração por stage antes/depois",
                        "Reverter a flag para false — mudança puramente "
                        "configuracional",
                        [ev_id],
                    )
                )

        # shuffle partitions
        sp = configs.get("spark.sql.shuffle.partitions")
        if sp is not None:
            try:
                n = int(sp.value)
            except ValueError:
                n = None
            if n is not None and (n < 50 or n > 1000):
                ev_id = ev("spark.sql.shuffle.partitions", sp.value, 0.7)
                findings.append(
                    Finding(
                        category=FindingCategory.CONFIGURATION,
                        severity=Severity.LOW,
                        status=FindingStatus.POSSIBLE,
                        explanation=(
                            f"spark.sql.shuffle.partitions={n} fora da "
                            "faixa comum (50-1000). Sem métricas de "
                            "shuffle, adequação é indeterminada — o default "
                            "200 não é universalmente errado."
                        ),
                        evidence_ids=[ev_id],
                        validation_steps=[
                            "Medir bytes por partição em execução real "
                            "(target ~100-200MB por partição)"
                        ],
                    )
                )

        # broadcast threshold vs executor memory
        bj = configs.get("spark.sql.autoBroadcastJoinThreshold")
        em = configs.get("spark.executor.memory")
        if bj is not None:
            bj_mb = _to_mb(bj.value)
            em_mb = _to_mb(em.value) if em else None
            if bj_mb is not None and bj_mb > 512:
                ev_id = ev("spark.sql.autoBroadcastJoinThreshold", bj.value, 0.7)
                mem_note = (
                    f"executor.memory={em.value} — broadcast de até "
                    f"{bj_mb:.0f}MB por task pode pressionar memória"
                    if em is not None
                    else "executor.memory não declarado — pressão indeterminada"
                )
                findings.append(
                    Finding(
                        category=FindingCategory.OUT_OF_MEMORY,
                        severity=Severity.MEDIUM,
                        status=FindingStatus.POSSIBLE,
                        explanation=(
                            f"autoBroadcastJoinThreshold={bj.value} alto "
                            f"(>512MB). {mem_note}. Broadcast grande sem "
                            "memória proporcional risca OOM de executor/"
                            "driver — nunca aumentar recursos sem avaliar "
                            "disponibilidade e custo de cluster."
                        ),
                        evidence_ids=[ev_id],
                        validation_steps=[
                            "Medir tamanho real das tabelas broadcastadas "
                            "e picos de memória"
                        ],
                    )
                )

        # executor memory low + OOM workload signal
        if em is not None:
            em_mb = _to_mb(em.value)
            oom_signal = bool(workload.get("oom_evidence"))
            if em_mb is not None and em_mb < 4096 and oom_signal:
                ev_id = ev(
                    "spark.executor.memory",
                    f"{em.value} + sinal OOM do workload",
                    0.75,
                )
                findings.append(
                    Finding(
                        category=FindingCategory.OUT_OF_MEMORY,
                        severity=Severity.MEDIUM,
                        status=FindingStatus.PROBABLE,
                        explanation=(
                            f"executor.memory={em.value} (<4g) combinado "
                            "com evidência de OOM no workload (contexto de "
                            "análise anterior). Aumento de memória tem "
                            "implicações diretas de custo e quota — "
                            "verificar disponibilidade antes de escalar."
                        ),
                        evidence_ids=[ev_id],
                        validation_steps=[
                            "Confirmar pico de memória por task no Spark UI",
                            "Avaliar quota/custo do aumento proposto",
                        ],
                    )
                )

        # CBO without stats signal
        cbo = configs.get("spark.sql.cbo.enabled")
        if cbo is not None and cbo.value.lower() == "true" and not workload.get("stats_available"):
            ev_id = ev("spark.sql.cbo.enabled", "true sem estatísticas conhecidas", 0.6)
            findings.append(
                Finding(
                    category=FindingCategory.CONFIGURATION,
                    severity=Severity.LOW,
                    status=FindingStatus.POSSIBLE,
                    explanation=(
                        "spark.sql.cbo.enabled=true sem evidência de "
                        "estatísticas coletadas — CBO sem stats tende a "
                        "não alterar planos (no-op) e adiciona overhead "
                        "de otimização."
                    ),
                    evidence_ids=[ev_id],
                    validation_steps=[
                        "Verificar DESCRIBE EXTENDED / ANALYZE TABLE nos "
                        "principais objetos"
                    ],
                )
            )

        # missing-runtime note on matrix-only configs when runtime unknown
        if spark_v is None and glue_v is None and configs:
            findings.append(
                Finding(
                    category=FindingCategory.CONFIGURATION,
                    severity=Severity.INFO,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        "Runtime (spark/glue version) não declarado — "
                        "aplicabilidade de cada config permanece "
                        "indeterminada; declare spark_version/glue_version "
                        "no contexto para avaliação precisa."
                    ),
                    evidence_ids=[],
                )
            )
