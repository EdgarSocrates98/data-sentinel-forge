"""Cycle 04 domain contracts — data quality, lineage, impact (§2.2).

Versioned additive contracts; same ``schema_version 1.0.0`` family as the
rest of the public surface. ``extra="forbid"`` like sibling contracts —
unknown fields are rejected at the boundary, not silently dropped.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import ConfigDict, Field

from data_sentinel.core.contracts.entities import (
    ContractModel,
    Evidence,
    Finding,
    UTCDateTime,
)


class RuleType(StrEnum):
    COMPLETENESS = "completeness"
    NOT_NULL = "not_null"
    UNIQUENESS = "uniqueness"
    UNIQUENESS_RATIO = "uniqueness_ratio"
    COMPLIANCE = "compliance"
    RANGE = "range"
    NUMERIC_RANGE = "numeric_range"
    FRESHNESS = "freshness"
    SCHEMA = "schema"
    SIZE = "size"
    ROW_COUNT = "row_count"
    ACCEPTED_VALUES = "accepted_values"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    STRING_PATTERN = "string_pattern"
    DATA_TYPE = "data_type"
    DISTRIBUTION = "distribution"
    BUSINESS_RULE = "business_rule"
    CUSTOM = "custom"


class ObservationStatus(StrEnum):
    PASS = "PASS"  # noqa: S105 - status de observação, não credencial
    FAIL = "FAIL"
    WARN = "WARN"
    UNKNOWN = "UNKNOWN"  # ausência de resultado nunca vira sucesso


class DriftLevel(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class DatasetReference(ContractModel):
    namespace: str = Field(min_length=1)
    name: str = Field(min_length=1)
    platform: str = ""
    catalog: str = ""
    account: str = ""
    region: str = ""
    version: str = ""
    identifier: str = ""


class QualityRule(ContractModel):
    rule_id: str = Field(min_length=1)
    rule_type: RuleType
    target: str = Field(min_length=1)  # column or dataset name
    expected: Any = None
    tolerance: float | None = Field(default=None, ge=0)
    severity: str = "medium"
    parameters: dict[str, Any] = Field(default_factory=dict)
    execution_requirements: list[str] = Field(default_factory=list)


class FreshnessPolicy(ContractModel):
    max_age_seconds: float | None = Field(default=None, gt=0)
    reference_field: str = ""


class DataQualityContract(ContractModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, populate_by_name=True
    )

    contract_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    dataset: DatasetReference
    schema_fields: dict[str, str] = Field(
        default_factory=dict, alias="schema"
    )  # col → type (serializes as "schema")
    constraints: list[str] = Field(default_factory=list)
    quality_rules: list[QualityRule] = Field(default_factory=list)
    freshness_policy: FreshnessPolicy | None = None
    owner: str = ""
    provenance: str = ""  # where the contract came from


class QualityObservation(ContractModel):
    """A normalized, observed quality measurement (§4.5)."""

    observation_id: str = Field(min_length=1)
    rule_id: str = ""
    dataset: DatasetReference | None = None
    run_id: str = ""
    timestamp: UTCDateTime | None = None  # may be absent — stays None
    observed_value: Any = None
    expected_value: Any = None
    status: ObservationStatus = ObservationStatus.UNKNOWN
    source: str = ""  # engine/adapter that produced it
    metric_name: str = ""  # original engine metric name, preserved
    unit: str = ""
    provenance: str = ""
    limitations: list[str] = Field(default_factory=list)


class QualityAssessment(ContractModel):
    assessment_id: str = Field(min_length=1)
    contract_version: str = ""
    execution_context: dict[str, str] = Field(default_factory=dict)
    observations: list[QualityObservation] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class LineageEvent(ContractModel):
    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)  # START/RUNNING/COMPLETE/...
    event_time: UTCDateTime | None = None
    run: dict[str, Any] = Field(default_factory=dict)
    job: dict[str, Any] = Field(default_factory=dict)
    inputs: list[DatasetReference] = Field(default_factory=list)
    outputs: list[DatasetReference] = Field(default_factory=list)
    facets: dict[str, Any] = Field(default_factory=dict)
    provenance: str = ""


class LineageKind(StrEnum):
    OBSERVED = "observed"  # runtime/OpenLineage — Sentinel territory
    STATIC = "static"  # declared in code/config — Doctor territory


class ImpactAssessment(ContractModel):
    target: DatasetReference
    upstream: list[DatasetReference] = Field(default_factory=list)
    downstream: list[DatasetReference] = Field(default_factory=list)
    affected_entities: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    graph_paths: list[list[str]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    potential_only: Literal[True] = True  # nunca impacto comprovado
