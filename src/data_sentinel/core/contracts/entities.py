"""Data Sentinel public domain entities (§4 contracts).

Every model serializes to stable JSON: snake_case keys, ISO-8601 UTC
timestamps, enum wire values. ``schema_version`` on DiagnosticReport tracks
the contract version constant.
"""

import hashlib
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Annotated, Any, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError

from data_sentinel.core.contracts.enums import (
    AnalysisMode,
    EvidenceProvenance,
    ExecutionStatus,
    FindingCategory,
    FindingStatus,
    Platform,
    Severity,
    SourceType,
)
from data_sentinel.core.exceptions import ContractValidationError

SCHEMA_VERSION = "1.0.0"


def _new_id() -> str:
    return uuid.uuid4().hex


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


UTCDateTime = Annotated[datetime, AfterValidator(_ensure_utc)]


class ContractModel(BaseModel):
    """Base for public contracts: forbid unknown fields, stable JSON, domain errors."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @classmethod
    def parse(cls, data: Mapping[str, Any] | str | bytes) -> Self:
        try:
            if isinstance(data, str | bytes):
                return cls.model_validate_json(data)
            return cls.model_validate(dict(data))
        except ValidationError as exc:
            raise ContractValidationError(
                code="contract.invalid",
                message=f"invalid {cls.__name__}",
                details={"errors": exc.errors(include_url=False)},
            ) from exc

    @classmethod
    def from_json(cls, payload: str | bytes) -> Self:
        return cls.parse(payload)

    def to_json(self) -> str:
        return self.model_dump_json()

    def content_sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode()).hexdigest()


class ArtifactReference(ContractModel):
    """Pointer to an input artifact (file, table, URI) under analysis."""

    uri: str = Field(min_length=1)
    description: str | None = None


class AccessMetadata(ContractModel):
    """How an evidence artifact was accessed."""

    accessed_by: str | None = None
    access_method: str | None = None


class Environment(ContractModel):
    """Environment a workload ran in."""

    name: str = Field(min_length=1)
    region: str | None = None
    details: dict[str, str] = Field(default_factory=dict)


class ExecutionContext(ContractModel):
    """Context identifying the workload execution under analysis."""

    job_name: str | None = None
    application_id: str | None = None
    environment: Environment | None = None
    extra: dict[str, str] = Field(default_factory=dict)


class RequestConstraints(ContractModel):
    """Limits the caller imposes on the analysis."""

    max_file_bytes: int | None = Field(default=None, gt=0)
    timeout_seconds: int | None = Field(default=None, gt=0)
    allowed_roots: list[str] = Field(default_factory=list)


class ResourceContext(ContractModel):
    """Observed resource shape of a workload execution."""

    executor_count: int | None = Field(default=None, ge=0)
    executor_memory: str | None = None
    executor_cores: int | None = Field(default=None, ge=0)
    details: dict[str, str] = Field(default_factory=dict)


class DiagnosticRequest(ContractModel):
    """Input describing what should be analyzed and how (§4)."""

    request_id: str = Field(default_factory=_new_id)
    source_type: SourceType
    artifact_references: list[ArtifactReference] = Field(min_length=1)
    execution_context: ExecutionContext | None = None
    platform: Platform
    runtime_version: str | None = None
    analysis_mode: AnalysisMode = AnalysisMode.BALANCED
    constraints: RequestConstraints | None = None


class Evidence(ContractModel):
    """A traceable excerpt supporting findings (§4)."""

    evidence_id: str = Field(default_factory=_new_id)
    source: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    captured_at: UTCDateTime
    content_hash: str = Field(min_length=1)
    sanitized_excerpt: str
    provenance: EvidenceProvenance
    confidence: float = Field(ge=0.0, le=1.0)
    access_metadata: AccessMetadata | None = None


class Finding(ContractModel):
    """An evidence-backed diagnostic conclusion (§4)."""

    finding_id: str = Field(default_factory=_new_id)
    category: FindingCategory
    severity: Severity
    status: FindingStatus
    explanation: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    validation_steps: list[str] = Field(default_factory=list)


class OptimizationRecommendation(ContractModel):
    """A proposed change with rationale, risk and rollback (§4)."""

    recommendation_id: str = Field(default_factory=_new_id)
    target: str = Field(min_length=1)
    proposed_change: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expected_effect: str | None = None
    estimated_risk: str | None = None
    validation_plan: str | None = None
    rollback_plan: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ExecutionMetadata(ContractModel):
    """Metadata about the job run the artifacts came from (§4)."""

    platform: Platform
    engine: str | None = None
    runtime: str | None = None
    run_id: str | None = None
    start_time: UTCDateTime | None = None
    end_time: UTCDateTime | None = None
    status: ExecutionStatus = ExecutionStatus.UNKNOWN
    resource_context: ResourceContext | None = None


class DiagnosticReport(ContractModel):
    """Versioned output contract aggregating findings (§4)."""

    report_id: str = Field(default_factory=_new_id)
    schema_version: str = Field(default=SCHEMA_VERSION)
    request_id: str
    created_at: UTCDateTime
    environment: Environment | None = None
    analyzer_versions: dict[str, str] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    summary: str = ""
    references: list[str] = Field(default_factory=list)


class CapabilityManifest(ContractModel):
    """Declared capabilities and limitations of an analyzer/component (§4)."""

    capability_id: str
    version: str
    supported_platforms: list[Platform] = Field(default_factory=list)
    supported_runtimes: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    supported_operations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
