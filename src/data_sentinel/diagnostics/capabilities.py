"""Capability discovery (Cycle 03.1 §5).

Converts registered analyzer manifests plus integration surfaces into
``CapabilityDescriptor`` records that an orchestrator (e.g. The Forge)
can consume — without making any of them mandatory at runtime.
"""

from __future__ import annotations

from data_sentinel.analyzers import registry
from data_sentinel.core.contracts import (
    INTEROP_SCHEMA_VERSION,
    CapabilityDescriptor,
)

_PROVIDER = "data-sentinel"


def analyzer_descriptors() -> list[CapabilityDescriptor]:
    """One descriptor per registered analyzer."""
    out: list[CapabilityDescriptor] = []
    for analyzer in registry.all():
        m = analyzer.capabilities()
        out.append(
            CapabilityDescriptor(
                capability_id=f"sentinel.{m.capability_id}",
                provider=_PROVIDER,
                version=m.version,
                input_types=list(m.supported_operations) or ["diagnostic-request"],
                output_types=["findings", "evidence", "recommendations"],
                permissions=list(m.required_permissions),
                limitations=list(m.limitations),
            )
        )
    return out


def integration_descriptors() -> list[CapabilityDescriptor]:
    """Non-analyzer capabilities (interop surfaces)."""
    return [
        CapabilityDescriptor(
            capability_id="sentinel.import.doctor-bundle",
            provider=_PROVIDER,
            version=INTEROP_SCHEMA_VERSION,
            input_types=["handoff-bundle@1", "forge-contracts/1",
                         "scan-json@3.0"],
            output_types=["external-diagnostic-bundle", "findings"],
            permissions=["filesystem:read"],
            limitations=[
                "import-only: não exporta bundles",
                "findings importados nunca são auto-CONFIRMED",
            ],
        ),
        CapabilityDescriptor(
            capability_id="sentinel.incident.graph",
            provider=_PROVIDER,
            version=INTEROP_SCHEMA_VERSION,
            input_types=["unified-execution-context", "findings", "evidence"],
            output_types=["evidence-graph", "incident-timeline"],
            limitations=[
                "correlação exige vínculo justificável (ids/refs compartilhadas)",
                "arestas causais são POTENTIALLY_CAUSED_BY, nunca comprovadas",
            ],
        ),
    ]


def all_descriptors() -> list[CapabilityDescriptor]:
    """Full capability inventory for discovery (deterministic order)."""
    descs = analyzer_descriptors() + integration_descriptors()
    return sorted(descs, key=lambda d: d.capability_id)
