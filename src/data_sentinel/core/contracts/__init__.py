"""Public, versioned domain contracts for Data Sentinel.

Only public contract types are re-exported here; internal implementation
types must never leak into this namespace.
"""

from data_sentinel.core.contracts.entities import (
    SCHEMA_VERSION,
    AccessMetadata,
    ArtifactReference,
    CapabilityManifest,
    ContractModel,
    DiagnosticReport,
    DiagnosticRequest,
    Environment,
    Evidence,
    ExecutionContext,
    ExecutionMetadata,
    Finding,
    OptimizationRecommendation,
    RequestConstraints,
    ResourceContext,
    UTCDateTime,
)
from data_sentinel.core.contracts.enums import (
    AnalysisMode,
    EvidenceProvenance,
    ExecutionStatus,
    FindingCategory,
    FindingStatus,
    Platform,
    Severity,
    SourceType,
    SupportStatus,
)
from data_sentinel.core.contracts.lakehouse import (
    AccessContext,
    CompatibilityAssessment,
    IcebergSnapshotSummary,
    IcebergTableMetadata,
    LakehouseOperation,
)

__all__ = [
    "SCHEMA_VERSION",
    "AccessContext",
    "AccessMetadata",
    "AnalysisMode",
    "ArtifactReference",
    "CapabilityManifest",
    "CompatibilityAssessment",
    "ContractModel",
    "DiagnosticReport",
    "DiagnosticRequest",
    "Environment",
    "Evidence",
    "EvidenceProvenance",
    "ExecutionContext",
    "ExecutionMetadata",
    "ExecutionStatus",
    "Finding",
    "FindingCategory",
    "FindingStatus",
    "IcebergSnapshotSummary",
    "IcebergTableMetadata",
    "LakehouseOperation",
    "OptimizationRecommendation",
    "Platform",
    "RequestConstraints",
    "ResourceContext",
    "Severity",
    "SourceType",
    "SupportStatus",
    "UTCDateTime",
]
