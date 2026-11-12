"""Cycle 09 — validated TypeScript client contracts.

`frontend/src/app/core/api.models.ts` is hand-maintained; this test
parses its `export interface` blocks and asserts the declared field
names match the authoritative Python wire shapes (pydantic model_fields
/ dataclass fields / literal endpoint keys). Drift in either direction
fails here instead of surfacing as silent UI mismatches.
"""

from __future__ import annotations

import re
from dataclasses import fields as dc_fields
from pathlib import Path

from data_sentinel.analyzers.spark.plans.models import ExecutionPlan, PlanNode
from data_sentinel.core.contracts.interop import CapabilityDescriptor
from data_sentinel.core.contracts.quality import QualityObservation
from data_sentinel.core.contracts.snapshot import ExecutionSnapshot
from data_sentinel.remediation.plans import RemediationPlan

TS_MODELS = Path(__file__).resolve().parents[2] / "frontend/src/app/core/api.models.ts"

_IFACE = re.compile(r"export interface (\w+)\s*\{(.*?)\n\}", re.S)
_FIELD = re.compile(r"^\s*(?:readonly\s+)?([A-Za-z_]\w*)\??:", re.M)


def _ts_interfaces() -> dict[str, set[str]]:
    text = TS_MODELS.read_text(encoding="utf-8")
    return {m.group(1): set(_FIELD.findall(m.group(2))) for m in _IFACE.finditer(text)}


# interface name → authoritative wire field names
_EXPECTED: dict[str, set[str]] = {
    "HealthResponse": {"status", "version", "api"},
    "CapabilityDescriptor": set(CapabilityDescriptor.model_fields),
    # GET /api/v1/tools → to_mcp_manifest entry keys
    "ToolManifestEntry": {"name", "description", "inputSchema"},
    "ExecutionSnapshot": set(ExecutionSnapshot.model_fields),
    "QualityObservation": set(QualityObservation.model_fields),
    "RemediationPlan": set(RemediationPlan.model_fields),
    "PlanNodeWire": {f.name for f in dc_fields(PlanNode)},
    "ExecutionPlanWire": {f.name for f in dc_fields(ExecutionPlan)},
}


def test_ts_models_file_exists() -> None:
    assert TS_MODELS.is_file()


def test_interfaces_cover_expected_set() -> None:
    found = _ts_interfaces()
    missing = set(_EXPECTED) - set(found)
    assert not missing, f"interfaces absentes em api.models.ts: {missing}"


def test_field_parity_with_python_wire_shapes() -> None:
    found = _ts_interfaces()
    for name, expected in _EXPECTED.items():
        got = found[name]
        extra = got - expected
        absent = expected - got
        assert not (extra or absent), (
            f"{name}: campos a mais no TS {sorted(extra)} / ausentes {sorted(absent)}"
        )
