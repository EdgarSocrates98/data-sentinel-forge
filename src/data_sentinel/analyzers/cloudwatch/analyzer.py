"""CloudWatch log analyzer — §4.2/4.3/4.6.

Reuses the Spark/Glue pattern library for finding generation (no duplicated
algorithms) and layers on event parsing, error correlation and the incident
timeline as structured metadata.
"""

import time
from collections.abc import Sequence
from dataclasses import replace

from data_sentinel.analyzers.cloudwatch.log_parser import parse_log_text
from data_sentinel.analyzers.protocol import AnalysisResult
from data_sentinel.analyzers.spark.log_analyzer import SparkGlueLogAnalyzer
from data_sentinel.core.contracts import (
    CapabilityManifest,
    DiagnosticRequest,
    FindingStatus,
    Platform,
    SourceType,
)
from data_sentinel.core.security.paths import InputFile
from data_sentinel.diagnostics.correlation import correlate
from data_sentinel.diagnostics.timeline import build_timeline


def _evidence_line(ev_location: str) -> int | None:
    """Extract ``path:lineno`` → lineno when present."""
    _, _, tail = ev_location.rpartition(":")
    return int(tail) if tail.isdigit() else None


class CloudWatchLogAnalyzer(SparkGlueLogAnalyzer):
    """Log analyzer for CloudWatch-exported artifacts."""

    @property
    def analyzer_id(self) -> str:
        return "cloudwatch-log-analyzer"

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (SourceType.CLOUDWATCH_LOG,)

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
            *super().limitations,
            "correlação primário/cascata é heurística documentada — revise antes de agir",
            "timestamps só entram na timeline quando observados no texto",
        )

    def analyze(
        self, request: DiagnosticRequest, inputs: Sequence[InputFile]
    ) -> AnalysisResult:
        started = time.monotonic()
        result = super().analyze(request, inputs)
        text = "\n".join(i.text for i in inputs)

        parsed = parse_log_text(text)
        correlation = correlate(parsed)
        timeline = build_timeline(parsed, only_exceptions=False)

        secondary_lines = {
            e.line_no for inc in correlation.incidents for e in inc.secondary
        }
        evidence_line_by_id = {
            ev.evidence_id: _evidence_line(ev.source_location) for ev in result.evidence
        }
        findings = []
        for finding in result.findings:
            ev_lines = {
                ln
                for ev_id in finding.evidence_ids
                if (ln := evidence_line_by_id.get(ev_id)) is not None
            }
            if ev_lines and ev_lines <= secondary_lines:
                finding = finding.model_copy(
                    update={
                        "status": FindingStatus.PROBABLE,
                        "explanation": finding.explanation
                        + " (assinatura observada apenas em posição secundária/cascata —"
                        " provável consequência de erro anterior)",
                    }
                )
            findings.append(finding)

        metadata = {
            **result.metadata,
            "correlation": {
                "incident_count": len(correlation.incidents),
                "total_exceptions": correlation.total_exceptions,
                "chained_count": correlation.chained_count,
                "primaries": [
                    {
                        "line_no": i.primary.line_no if i.primary else None,
                        "exception_class": i.primary.exception_class if i.primary else None,
                        "secondary_count": i.secondary_count,
                    }
                    for i in correlation.incidents
                ],
            },
            "timeline": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "summary": e.summary,
                    "exception_class": e.exception_class,
                    "line_no": e.line_no,
                }
                for e in timeline.entries
            ],
            "timeline_undated_lines": timeline.undated_lines,
        }
        return replace(
            result,
            analyzer_id=self.analyzer_id,
            findings=findings,
            metadata=metadata,
            duration_ms=int((time.monotonic() - started) * 1000),
        )

    def capabilities(self) -> CapabilityManifest:
        m = super().capabilities()
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=[Platform.AWS_GLUE, Platform.GENERIC],
            supported_runtimes=m.supported_runtimes,
            required_permissions=m.required_permissions,
            supported_operations=[*m.supported_operations, "correlate_errors", "build_timeline"],
            limitations=list(self.limitations),
        )
