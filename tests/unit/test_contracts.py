"""Unit tests for the public domain contracts."""

from datetime import UTC, datetime

import pytest

from data_sentinel.core.contracts import (
    SCHEMA_VERSION,
    AnalysisMode,
    ArtifactReference,
    CapabilityManifest,
    DiagnosticReport,
    DiagnosticRequest,
    Evidence,
    EvidenceProvenance,
    ExecutionMetadata,
    ExecutionStatus,
    Finding,
    FindingCategory,
    FindingStatus,
    OptimizationRecommendation,
    Platform,
    Severity,
    SourceType,
)
from data_sentinel.core.exceptions import ContractValidationError

NOW = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)


def sample_request() -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=SourceType.LOG,
        artifact_references=[ArtifactReference(uri="fixtures/logs/job.log")],
        platform=Platform.AWS_GLUE,
        analysis_mode=AnalysisMode.BALANCED,
    )


def sample_evidence() -> Evidence:
    return Evidence(
        source="log",
        source_location="fixtures/logs/job.log:42",
        captured_at=NOW,
        content_hash="a" * 64,
        sanitized_excerpt="java.lang.OutOfMemoryError",
        provenance=EvidenceProvenance.OBSERVED,
        confidence=0.95,
    )


def sample_finding() -> Finding:
    return Finding(
        category=FindingCategory.OUT_OF_MEMORY,
        severity=Severity.HIGH,
        status=FindingStatus.CONFIRMED,
        explanation="Driver OOM indicated by log evidence",
        evidence_ids=["ev-1"],
        alternatives=["disk pressure"],
        recommendations=["rec-1"],
        validation_steps=["increase driver memory and rerun"],
    )


def sample_report() -> DiagnosticReport:
    return DiagnosticReport(
        request_id="req-1",
        created_at=NOW,
        analyzer_versions={"log-analyzer": "0.1.0"},
        findings=[sample_finding()],
        limitations=["no executor metrics available"],
        summary="1 finding",
        references=["https://docs.aws.amazon.com/glue/"],
    )


class TestConstruction:
    def test_request_valid(self) -> None:
        req = sample_request()
        assert req.request_id
        assert req.platform is Platform.AWS_GLUE

    def test_report_has_schema_version(self) -> None:
        assert sample_report().schema_version == SCHEMA_VERSION

    def test_all_entities_construct(self) -> None:
        OptimizationRecommendation(
            target="spark.executor.memory",
            proposed_change="raise to 8g",
            rationale="OOM on executors",
            expected_effect="fewer spills",
            estimated_risk="low",
            validation_plan="rerun job",
            rollback_plan="revert config",
            evidence_ids=["ev-1"],
        )
        ExecutionMetadata(
            platform=Platform.SPARK,
            engine="spark",
            runtime="3.5",
            run_id="app-123",
            start_time=NOW,
            end_time=NOW,
            status=ExecutionStatus.SUCCEEDED,
        )
        CapabilityManifest(
            capability_id="spark-log-analyzer",
            version="0.1.0",
            supported_platforms=[Platform.SPARK, Platform.AWS_GLUE],
            supported_runtimes=["log4j"],
            required_permissions=[],
            supported_operations=["analyze_log"],
            limitations=["regex-based"],
        )


class TestValidation:
    def test_empty_artifact_references_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            DiagnosticRequest.parse(
                {"source_type": "log", "artifact_references": [], "platform": "spark"}
            )

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ContractValidationError):
            Evidence.parse(
                {
                    "source": "log",
                    "source_location": "x:1",
                    "captured_at": NOW.isoformat(),
                    "content_hash": "abc",
                    "sanitized_excerpt": "x",
                    "provenance": "observed",
                    "confidence": 1.5,
                }
            )

    def test_naive_datetime_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            Evidence.parse(
                {
                    "source": "log",
                    "source_location": "x:1",
                    "captured_at": "2026-10-19T12:00:00",
                    "content_hash": "abc",
                    "sanitized_excerpt": "x",
                    "provenance": "observed",
                    "confidence": 0.5,
                }
            )

    def test_unknown_fields_forbidden(self) -> None:
        with pytest.raises(ContractValidationError):
            Finding.parse(
                {
                    "category": "unknown",
                    "severity": "LOW",
                    "status": "CONFIRMED",
                    "explanation": "x",
                    "bogus": 1,
                }
            )

    def test_bad_enum_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            DiagnosticRequest.parse(
                {
                    "source_type": "log",
                    "artifact_references": [{"uri": "x"}],
                    "platform": "spark",
                    "analysis_mode": "ultra",
                }
            )


class TestRoundTrip:
    @pytest.mark.parametrize(
        "model",
        [
            sample_request(),
            sample_evidence(),
            sample_finding(),
            sample_report(),
            OptimizationRecommendation(
                target="t", proposed_change="c", rationale="r"
            ),
            ExecutionMetadata(platform=Platform.SPARK),
            CapabilityManifest(capability_id="c", version="1"),
        ],
        ids=lambda m: type(m).__name__,
    )
    def test_json_round_trip(self, model: object) -> None:
        payload = model.to_json()  # type: ignore[attr-defined]
        restored = type(model).from_json(payload)  # type: ignore[attr-defined]
        assert restored == model
        assert restored.to_json() == payload  # type: ignore[attr-defined]

    def test_wire_format_uses_enum_values_and_iso(self) -> None:
        payload = sample_report().to_json()
        assert '"CONFIRMED"' in payload
        assert "2026-10-19T12:00:00Z" in payload
        assert '"schema_version":"1.0.0"' in payload


class TestEnums:
    def test_finding_status_taxonomy(self) -> None:
        assert {s.value for s in FindingStatus} == {
            "CONFIRMED",
            "PROBABLE",
            "POSSIBLE",
            "UNKNOWN",
        }

    def test_analysis_modes(self) -> None:
        assert {m.value for m in AnalysisMode} == {
            "economy",
            "balanced",
            "deep",
            "offline",
        }

    def test_provenance_values(self) -> None:
        assert {p.value for p in EvidenceProvenance} == {
            "declared",
            "static_inferred",
            "observed",
        }
