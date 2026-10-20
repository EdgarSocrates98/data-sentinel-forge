"""Unit + integration tests for the Spark/Glue log analyzer."""

from pathlib import Path

import pytest

from data_sentinel.analyzers import AnalyzerRegistry, registry
from data_sentinel.analyzers.spark import LOG_PATTERNS, SparkGlueLogAnalyzer
from data_sentinel.core.contracts import (
    AnalysisMode,
    ArtifactReference,
    DiagnosticRequest,
    FindingStatus,
    Platform,
    SourceType,
)
from data_sentinel.core.exceptions import InputValidationError, SentinelError
from data_sentinel.core.security import read_input_file

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "logs"
ANALYZER = SparkGlueLogAnalyzer()


def request_for(name: str, source: SourceType = SourceType.LOG) -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=source,
        artifact_references=[ArtifactReference(uri=str(FIXTURES / name))],
        platform=Platform.AWS_GLUE,
        analysis_mode=AnalysisMode.BALANCED,
    )


def inputs_for(name: str) -> list:
    return [read_input_file(FIXTURES / name, max_file_bytes=1_000_000)]


class TestDetection:
    @pytest.mark.parametrize(
        ("fixture", "pattern_id", "status"),
        [
            ("glue_oom.log", "oom-java", FindingStatus.CONFIRMED),
            ("executor_loss.log", "executor-lost-retry", FindingStatus.PROBABLE),
            ("disk_full.log", "disk-space", FindingStatus.CONFIRMED),
            ("disk_spill.log", "disk-spill-warn", FindingStatus.POSSIBLE),
            ("spark_exception.log", "spark-exception", FindingStatus.PROBABLE),
            ("access_denied.log", "aws-access-denied", FindingStatus.CONFIRMED),
            ("iceberg_error.log", "iceberg-catalog", FindingStatus.CONFIRMED),
            ("timeout.log", "job-timeout", FindingStatus.CONFIRMED),
            ("python_worker.log", "python-worker", FindingStatus.PROBABLE),
            ("missing_dep.log", "missing-dependency", FindingStatus.CONFIRMED),
        ],
    )
    def test_pattern_detected(
        self, fixture: str, pattern_id: str, status: FindingStatus
    ) -> None:
        result = ANALYZER.analyze(request_for(fixture), inputs_for(fixture))
        pattern = next(p for p in LOG_PATTERNS if p.pattern_id == pattern_id)
        hits = [
            f
            for f in result.findings
            if f.category == pattern.category and f.status == status
        ]
        assert hits, f"{pattern_id} not detected in {fixture}: {result.findings}"

    def test_mixed_log_yields_multiple_findings(self) -> None:
        result = ANALYZER.analyze(request_for("mixed.log"), inputs_for("mixed.log"))
        assert len(result.findings) >= 2
        categories = {f.category for f in result.findings}
        assert len(categories) >= 2

    def test_unrecognized_log_is_unknown_not_confirmed(self) -> None:
        result = ANALYZER.analyze(
            request_for("unrecognized.log"), inputs_for("unrecognized.log")
        )
        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.status is FindingStatus.UNKNOWN
        assert finding.evidence_ids == []
        assert result.evidence == []
        assert any("insuficiente" in f.explanation.lower() for f in result.findings)

    def test_evidence_linked_and_sanitized(self) -> None:
        result = ANALYZER.analyze(
            request_for("access_denied.log"), inputs_for("access_denied.log")
        )
        assert result.evidence
        finding = result.findings[0]
        assert finding.evidence_ids
        for evidence_id in finding.evidence_ids:
            ev = next(e for e in result.evidence if e.evidence_id == evidence_id)
            assert "access_denied.log:" in ev.source_location
            assert ev.sanitized_excerpt
            assert len(ev.content_hash) == 64

    def test_evidence_is_secret_redacted(self, tmp_path: Path) -> None:
        hostile = tmp_path / "hostile.log"
        hostile.write_text(
            "ERROR: OutOfMemoryError password=topsecret123\n"
        , encoding="utf-8")
        f = read_input_file(
            hostile, max_file_bytes=1_000_000, allowed_roots=[tmp_path]
        )
        result = ANALYZER.analyze(request_for("hostile.log"), [f])
        assert result.evidence
        for ev in result.evidence:
            assert "topsecret123" not in ev.sanitized_excerpt

    def test_findings_sorted_by_severity(self) -> None:
        result = ANALYZER.analyze(request_for("mixed.log"), inputs_for("mixed.log"))
        ranks = [
            ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"].index(f.severity.value)
            for f in result.findings
        ]
        assert ranks == sorted(ranks, reverse=True)


class TestValidationAndRegistry:
    def test_rejects_unsupported_source_type(self) -> None:
        with pytest.raises(InputValidationError):
            ANALYZER.analyze(
                request_for("x", SourceType.SQL_QUERY),
                inputs_for("glue_oom.log"),
            )

    def test_rejects_empty_inputs(self) -> None:
        with pytest.raises(InputValidationError):
            ANALYZER.analyze(request_for("x"), [])

    def test_registry_has_analyzer(self) -> None:
        assert any(
            a.analyzer_id == "spark-glue-log-analyzer" for a in registry.all()
        )

    def test_registry_lookup_by_source_type(self) -> None:
        found = registry.for_source_type(SourceType.LOG)
        assert any(a.analyzer_id == "spark-glue-log-analyzer" for a in found)

    def test_duplicate_registration_rejected(self) -> None:
        reg = AnalyzerRegistry()
        reg.register(SparkGlueLogAnalyzer())
        with pytest.raises(SentinelError):
            reg.register(SparkGlueLogAnalyzer())

    def test_capability_manifest_valid(self) -> None:
        manifest = ANALYZER.capabilities()
        assert manifest.capability_id == "spark-glue-log-analyzer"
        assert manifest.limitations

    def test_pattern_library_is_data_driven(self) -> None:
        assert len(LOG_PATTERNS) >= 8
        for pattern in LOG_PATTERNS:
            assert pattern.regexes
            assert pattern.title and pattern.rationale
