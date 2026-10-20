"""Cycle 03 §2.1 — lakehouse domain models (additive, schema 1.0.0).

These describe *metadata about* tables/access — never the tables
themselves. Provenance fields record whether a value was observed,
declared, inferred or left unverified.
"""

from typing import Any

from pydantic import Field

from data_sentinel.core.contracts.entities import ContractModel, Evidence
from data_sentinel.core.contracts.enums import SupportStatus


class IcebergTableMetadata(ContractModel):
    """Identity slice of an Iceberg table's metadata.json (§2.1)."""

    table_identifier: str = ""
    catalog_identifier: str = ""
    namespace: list[str] = Field(default_factory=list)
    metadata_location: str = ""
    format_version: int | None = None
    schema_id: int | None = None
    partition_spec_id: int | None = None
    sort_order_id: int | None = None
    current_snapshot_id: int | None = None
    properties: dict[str, str] = Field(default_factory=dict)
    provenance: str = "declared"  # declared | observed | inferred


class IcebergSnapshotSummary(ContractModel):
    """One snapshot as declared by table metadata (§2.1)."""

    snapshot_id: int
    parent_snapshot_id: int | None = None
    timestamp_ms: int | None = None
    operation: str = ""
    sequence_number: int | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    referenced_manifests: list[str] = Field(default_factory=list)
    source: str = "declared"
    completeness: str = "declared"  # declared | partial | unknown


class AccessContext(ContractModel):
    """Who is trying to do what, on which table, from which account (§2.1)."""

    source_account: str = ""
    destination_account: str = ""
    principal: str = ""
    region: str = ""
    catalog: str = ""
    database: str = ""
    table: str = ""
    resource_link: str = ""
    lf_mode: str = "unknown"  # iam | fgac | fta | legacy | unknown
    required_operation: str = ""
    observed_permissions: list[str] = Field(default_factory=list)
    unknown_permissions: list[str] = Field(default_factory=list)


class CompatibilityAssessment(ContractModel):
    """Verdict for a (runtime, engine, format, catalog, mode, op) tuple (§2.1)."""

    runtime: str = ""
    spark_version: str = ""
    iceberg_version: str = ""
    catalog_type: str = ""
    access_mode: str = ""
    operation: str = ""
    support_status: SupportStatus = SupportStatus.NOT_VERIFIED
    constraints: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    documentation_references: list[str] = Field(default_factory=list)


class LakehouseOperation(ContractModel):
    """A DML/DDL operation under analysis (§2.1)."""

    operation_type: str = ""
    input_tables: list[str] = Field(default_factory=list)
    output_table: str = ""
    target_namespace: list[str] = Field(default_factory=list)
    predicate: str = ""
    schema_requirements: list[str] = Field(default_factory=list)
    authorization_requirements: list[str] = Field(default_factory=list)
    compatibility_requirements: list[str] = Field(default_factory=list)


__all__ = [
    "AccessContext",
    "CompatibilityAssessment",
    "IcebergSnapshotSummary",
    "IcebergTableMetadata",
    "LakehouseOperation",
]
