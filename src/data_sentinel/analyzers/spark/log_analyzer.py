"""Deterministic log analyzer for Spark and AWS Glue artifacts (§01.3)."""

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime

from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.analyzers.spark.patterns import LOG_PATTERNS, LogPattern
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

MAX_EVIDENCE_PER_FINDING = 3


class SparkGlueLogAnalyzer(Analyzer):
    """Regex/heuristic classifier over Spark/Glue log4j-style output.

    Never fabricates diagnoses: unmatched input produces a single UNKNOWN
    finding stating what was analyzed and what would help.
    """

    @property
    def analyzer_id(self) -> str:
        return "spark-glue-log-analyzer"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (SourceType.LOG, SourceType.OTHER)

    @property
    def supported_platforms(self) -> tuple[str, ...]:
        return ("spark", "aws_glue", "databricks", "generic")

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
            "Baseado em padrões regex curados — não cobre erros fora da biblioteca",
            "Sem métricas de executor (Spark UI/event log não analisados neste ciclo)",
            "Sinal POSSIBLE/PROBABLE exige corroboração humana antes de agir",
        )

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=[],
            supported_runtimes=["log4j", "glue-stdout"],
            required_permissions=["filesystem:read"],
            supported_operations=["analyze_log"],
            limitations=list(self.limitations),
        )

    def analyze(self, request: DiagnosticRequest, inputs: Sequence[InputFile]) -> AnalysisResult:
        self.validate_input(request, inputs)
        captured = datetime.now(UTC)

        findings: list[Finding] = []
        evidence: list[Evidence] = []
        limitations: list[str] = list(self.limitations)
        matched: dict[str, list[tuple[LogPattern, InputFile, int, str, str]]] = {}

        for input_file in inputs:
            digest = hashlib.sha256(input_file.text.encode()).hexdigest()
            for lineno, line in enumerate(input_file.text.splitlines(), start=1):
                for pattern in LOG_PATTERNS:
                    if pattern.matches(line):
                        matched.setdefault(pattern.pattern_id, []).append(
                            (pattern, input_file, lineno, line, digest)
                        )

        for hits in matched.values():
            pattern = hits[0][0]
            finding_evidence_ids: list[str] = []
            for _pat, file, lineno, line, digest in hits[:MAX_EVIDENCE_PER_FINDING]:
                excerpt = sanitize_evidence_excerpt(
                    line.strip(), max_chars=500
                )
                ev = Evidence(
                    source="log",
                    source_location=f"{file.path}:{lineno}",
                    captured_at=captured,
                    content_hash=digest,
                    sanitized_excerpt=excerpt,
                    provenance=EvidenceProvenance.OBSERVED,
                    confidence=pattern.confidence,
                )
                evidence.append(ev)
                finding_evidence_ids.append(ev.evidence_id)
            extra = len(hits) - MAX_EVIDENCE_PER_FINDING
            explanation = (
                f"{pattern.rationale} {len(hits)} ocorrência(s) no log analisado."
            )
            if extra > 0:
                explanation += f" {extra} ocorrência(s) adicionais não exibidas."
            findings.append(
                Finding(
                    category=pattern.category,
                    severity=pattern.severity,
                    status=pattern.status,
                    explanation=explanation,
                    evidence_ids=finding_evidence_ids,
                    alternatives=list(pattern.suggested_actions[:2]),
                    recommendations=list(pattern.suggested_actions),
                    validation_steps=list(pattern.validation_steps),
                )
            )

        if not findings:
            limitations.append(
                "Nenhum padrão conhecido detectado — envie spark event log, "
                "plano físico (EXPLAIN) ou métricas de executor para análise "
                "mais profunda."
            )
            findings.append(
                Finding(
                    category=FindingCategory.UNKNOWN,
                    severity=Severity.INFO,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        "Evidência insuficiente: o log não contém nenhuma das "
                        f"{len(LOG_PATTERNS)} assinaturas de falha conhecidas "
                        f"por '{self.analyzer_id}'. Nenhum diagnóstico é "
                        "afirmado; classifique manualmente ou envie artefatos "
                        "adicionais."
                    ),
                    evidence_ids=[],
                    alternatives=[
                        "spark event log",
                        "plano físico da query",
                        "métricas do CloudWatch/Glue",
                    ],
                    recommendations=[],
                    validation_steps=[],
                )
            )

        return AnalysisResult(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.version,
            request_id=request.request_id,
            findings=sorted(
                findings,
                key=lambda f: list(Severity).index(f.severity)
                if f.severity in Severity
                else 0,
                reverse=True,
            ),
            evidence=evidence,
            limitations=limitations,
        )
