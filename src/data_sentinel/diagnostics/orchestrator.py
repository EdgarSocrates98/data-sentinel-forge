"""Deterministic diagnostic orchestrator (§9).

Pipeline: registry analyzers → results → report assembly. No LLM in the
path; interfaces are agent-ready (explicit in/out contracts) but not
agent-dependent. An analyzer failure degrades to a limitation — it never
silently drops or fabricates results.
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.analyzers.registry import registry
from data_sentinel.core.contracts import (
    DiagnosticReport,
    DiagnosticRequest,
    Evidence,
    Finding,
    OptimizationRecommendation,
    SourceType,
)
from data_sentinel.core.exceptions import SentinelError
from data_sentinel.core.security import InputFile


@dataclass(frozen=True)
class AnalysisLimits:
    """Plumbing for cancellation/caps — agent-ready but deterministic."""

    max_analyzers: int = 16
    timeout_ms: int = 60_000
    cancelled: bool = False


@dataclass
class DiagnosticOutcome:
    report: DiagnosticReport
    evidence: list[Evidence] = field(default_factory=list)
    results: list[AnalysisResult] = field(default_factory=list)
    recommendations: list[OptimizationRecommendation] = field(default_factory=list)
    analyzers_run: list[str] = field(default_factory=list)
    analyzers_skipped: list[str] = field(default_factory=list)


def _status_counts(findings: Sequence[Finding]) -> str:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.status.value] = counts.get(f.status.value, 0) + 1
    return (
        f"{len(findings)} achado(s): "
        + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        if findings
        else "nenhum achado"
    )


def run_diagnostics(
    request: DiagnosticRequest,
    inputs: Sequence[InputFile],
    *,
    analyzers: Sequence[Analyzer] | None = None,
    limits: AnalysisLimits | None = None,
) -> DiagnosticOutcome:
    """Run the analyzer set over inputs and assemble a DiagnosticReport.

    Analyzer selection: explicit list or registry lookup by source_type.
    """
    limits = limits or AnalysisLimits()
    started = time.monotonic()

    selected = list(analyzers) if analyzers is not None else registry.for_source_type(
        request.source_type
    )
    if not selected:
        raise SentinelError(
            code="orquestrador.sem_analisador",
            message=(
                f"nenhum analyzer registrado para '{request.source_type.value}'"
            ),
            details={"source_type": request.source_type.value},
        )

    outcome = DiagnosticOutcome(
        report=None,  # type: ignore[arg-type]
    )
    seen_limitations: set[str] = set()
    failure_notes: list[str] = []

    for analyzer in selected[: limits.max_analyzers]:
        if limits.cancelled or (
            time.monotonic() - started
        ) * 1000 > limits.timeout_ms:
            outcome.analyzers_skipped.append(analyzer.analyzer_id)
            continue
        try:
            t0 = time.monotonic()
            result = analyzer.analyze(request, inputs)
            if result.duration_ms is None:
                result = replace(
                    result, duration_ms=int((time.monotonic() - t0) * 1000)
                )
        except Exception as exc:  # analyzer fault → limitation, never fabricate
            outcome.analyzers_skipped.append(analyzer.analyzer_id)
            failure_note = f"analyzer '{analyzer.analyzer_id}' falhou: {exc!r}"
            if failure_note not in seen_limitations:
                seen_limitations.add(failure_note)
                failure_notes.append(failure_note)
            continue
        outcome.results.append(result)
        outcome.analyzers_run.append(analyzer.analyzer_id)

    findings = [f for r in outcome.results for f in r.findings]
    outcome.evidence = [e for r in outcome.results for e in r.evidence]

    limitations: list[str] = list(failure_notes)
    for r in outcome.results:
        for lim in r.limitations:
            if lim not in seen_limitations:
                seen_limitations.add(lim)
                limitations.append(lim)
    if outcome.analyzers_skipped:
        limitations.append(
            "analyzers não executados: " + ", ".join(outcome.analyzers_skipped)
        )

    for r in outcome.results:
        raw_recs = r.metadata.get("recommendations")
        if not isinstance(raw_recs, list):
            continue
        for rec in raw_recs:
            if isinstance(rec, OptimizationRecommendation):
                outcome.recommendations.append(rec)
            elif isinstance(rec, dict):
                outcome.recommendations.append(OptimizationRecommendation(**rec))

    captured = datetime.now(UTC)
    outcome.report = DiagnosticReport(
        request_id=request.request_id,
        created_at=captured,
        analyzer_versions={r.analyzer_id: r.analyzer_version for r in outcome.results},
        findings=findings,
        limitations=limitations,
        summary=_status_counts(findings),
        references=[a.uri for a in request.artifact_references],
        recommendations=outcome.recommendations,
    )
    return outcome


def analyzers_for(source_type: SourceType) -> list[Analyzer]:
    return registry.for_source_type(source_type)
