"""Interoperability contracts (Cycle 03.1).

Models the ``forge-contracts/1`` wire vocabulary used by Forge Doctor
products plus the Sentinel-side ``ExternalDiagnosticBundle`` envelope.

Design rules (prompt §3):
- ``extra="allow"`` preserves unknown / ``x-*`` extension keys instead of
  dropping them (forward compatibility).
- Only the minimal required core fields are enforced; producers differ.
- Nothing here imports Forge Doctor code — pure contracts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

INTEROP_SCHEMA_VERSION: Literal["1.0.0"] = "1.0.0"
FORGE_CONTRACTS_1 = "forge-contracts/1"

SUPPORTED_CONTRACT_VERSIONS = {FORGE_CONTRACTS_1, "1", 1}


class ContractItem(BaseModel):
    """Base for per-item contract payloads; keeps ``contract_version``."""

    model_config = ConfigDict(extra="allow")

    contract_version: str | int | None = None


class InteropEvidence(ContractItem):
    kind: str | None = None
    ref: str | None = None
    source: str | None = None
    detail: str | None = None


class InteropFinding(ContractItem):
    """forge-contracts/1 finding (doctor-data shape: check_id/message)."""

    check_id: str | None = None
    id: str | None = None  # doctor-api shape
    title: str | None = None
    message: str | None = None
    description: str | None = None  # doctor-api shape
    severity: str | None = None
    confidence: str | None = None
    category: str | None = None
    evidence: list[InteropEvidence | str] | str = Field(default_factory=list)
    evidence_kind: str | None = None
    recommendation: str | None = None
    remediation: str | None = None
    fixable: bool | None = None
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    fingerprint: str | None = None
    file: str | None = None
    line: int | None = None
    entity_ids: list[str] = Field(default_factory=list)
    unknowns: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def external_id(self) -> str:
        return self.check_id or self.id or "unknown"

    @property
    def text(self) -> str:
        return self.message or self.description or self.title or ""


class InteropEntity(ContractItem):
    id: str | None = None
    kind: str | None = None
    domain: str | None = None
    identifier: str | None = None
    name: str | None = None
    file: str | None = None
    line: int | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)


class InteropRelationship(ContractItem):
    kind: str | None = None
    src: str | None = None
    dst: str | None = None
    evidence_kind: str | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)


class InteropCapability(ContractItem):
    id: str | None = None
    domain: str | None = None
    status: str | None = None
    confidence: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class InteropUnknownFact(ContractItem):
    kind: str | None = None
    subject: str | None = None
    missing: str | None = None
    reason: str | None = None
    detail: str | None = None
    source: str | None = None


class InteropPlan(ContractItem):
    id: str | None = None
    check_id: str | None = None
    problem: str | None = None
    actions: list[dict[str, Any]] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    requires_approval: bool | None = None


class ToolRef(BaseModel):
    """Producer identification (``tool`` block in real bundles)."""

    model_config = ConfigDict(extra="allow")

    name: str
    version: str | None = None


class IntegrityMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    content_sha256: str | None = None
    received_sha256: str | None = None
    byte_size: int | None = None


class ExternalDiagnosticBundle(BaseModel):
    """Sentinel-side interop envelope (§3.1).

    ``schema_version`` is the Sentinel interop envelope version (1.0.0);
    ``contract_version`` carries the producer's contract tag when present
    (``forge-contracts/1`` or legacy int ``1``).
    """

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["1.0.0"] = INTEROP_SCHEMA_VERSION
    contract_version: str | int | None = None
    producer: ToolRef
    generated_at: str | None = None
    source_references: list[str] = Field(default_factory=list)

    findings: list[InteropFinding] = Field(default_factory=list)
    evidence: list[InteropEvidence] = Field(default_factory=list)
    entities: list[InteropEntity] = Field(default_factory=list)
    relationships: list[InteropRelationship] = Field(default_factory=list)
    capabilities: list[InteropCapability] = Field(default_factory=list)
    unknowns: list[InteropUnknownFact] = Field(default_factory=list)
    plans: list[InteropPlan] = Field(default_factory=list)

    limitations: list[str] = Field(default_factory=list)
    integrity: IntegrityMetadata | None = None
    project: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)


class CapabilityDescriptor(BaseModel):
    """§3.1 capability descriptor for discovery (ds-0035 consumer)."""

    model_config = ConfigDict(extra="forbid")

    capability_id: str
    provider: str
    version: str
    input_types: list[str] = Field(default_factory=list)
    output_types: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
