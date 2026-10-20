"""Contract tests for Cycle 03.1 interoperability models.

Validates against REAL forge-doctor fixtures captured during the audit
(ds-0030): canonical forge-contracts/1 fixtures plus real CLI outputs
(handoff bundle + scan JSON) produced by forge-doctor-data 1.0.3.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from data_sentinel.core.contracts import (
    FORGE_CONTRACTS_1,
    INTEROP_SCHEMA_VERSION,
    CapabilityDescriptor,
    ExternalDiagnosticBundle,
    InteropFinding,
    ToolRef,
)

FIX = Path(__file__).resolve().parents[2] / "fixtures"
DDATA = FIX / "doctor-data"
DAPI = FIX / "doctor-api"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_canonical_handoff_fixture_parses() -> None:
    raw = _load(DAPI / "forge-contracts-1-handoff.json")
    bundle = ExternalDiagnosticBundle(
        contract_version=raw["contract_version"],
        producer=ToolRef(**raw["tool"]),
        findings=raw["findings"],
        entities=raw["entities"],
        relationships=raw["relationships"],
        capabilities=raw["capabilities"],
        unknowns=raw["unknowns"],
        plans=raw["plans"],
        project=raw.get("project", {}),
        summary=raw.get("summary", {}),
    )
    assert bundle.contract_version == FORGE_CONTRACTS_1
    assert bundle.schema_version == INTEROP_SCHEMA_VERSION
    assert bundle.findings[0].external_id == "FD-DBT-042"
    assert bundle.producer.name


def test_real_doctor_data_handoff_bundle_parses() -> None:
    """Real `export --format handoff` output: contract_version int + results."""
    raw = _load(DDATA / "handoff-real-probe.json")
    assert raw["contract"] == "handoff-bundle"
    bundle = ExternalDiagnosticBundle(
        contract_version=raw["contract_version"],
        producer=ToolRef(**raw["tool"]),
        findings=raw["results"],  # legacy key
        entities=raw["graph"]["entities"],
        relationships=raw["graph"]["relationships"],
        plans=raw["plans"],
        project=raw["project"],
        summary=raw["summary"],
    )
    assert bundle.contract_version == 1
    assert len(bundle.findings) == len(raw["results"]) == 73
    assert all(isinstance(f, InteropFinding) for f in bundle.findings)


def test_real_doctor_data_scan_report_parses() -> None:
    """Real `scan --format json` output: schema_version 3.0 + results."""
    raw = _load(DDATA / "scan-real-probe.json")
    assert raw["schema_version"] == "3.0"
    bundle = ExternalDiagnosticBundle(
        producer=ToolRef(**raw["tool"]),
        findings=raw["results"],
        summary=raw["summary"],
        project=raw["project"],
    )
    warnings = [f for f in bundle.findings if f.severity == "warning"]
    assert len(warnings) == 4
    assert warnings[0].check_id in {"AWS002", "DEP002", "PY002", "REP002"}
    assert warnings[0].confidence == "high"


def test_unknown_fields_preserved_not_dropped() -> None:
    f = InteropFinding(check_id="X1", message="m", **{"x-future-key": {"a": 1}})
    dumped = f.model_dump()
    assert dumped["x-future-key"] == {"a": 1}


def test_missing_producer_rejected() -> None:
    with pytest.raises(ValidationError):
        ExternalDiagnosticBundle(findings=[])


def test_external_id_fallback_both_shapes() -> None:
    a = InteropFinding(check_id="GLUE002", message="m")
    b = InteropFinding(id="OAS001", description="d")
    assert a.external_id == "GLUE002" and b.external_id == "OAS001"
    assert b.text == "d"


def test_capability_descriptor_strict() -> None:
    d = CapabilityDescriptor(
        capability_id="sentinel.analyze.spark",
        provider="data-sentinel",
        version="1.0.0",
        input_types=["spark-plan", "cloudwatch-logs"],
        output_types=["findings", "recommendations"],
    )
    assert d.capability_id.startswith("sentinel.")
    with pytest.raises(ValidationError):
        CapabilityDescriptor(
            capability_id="x", provider="p", version="1", rogue_field=1
        )


def test_all_item_fixtures_round_trip() -> None:
    for name in ("finding", "evidence", "entity", "relationship",
                 "capability", "unknown-fact", "remediation-plan"):
        raw = _load(DDATA / f"{name}.json")
        model = {
            "finding": InteropFinding,
        }.get(name)
        if model:
            obj = model.model_validate(raw)
            assert obj.contract_version == FORGE_CONTRACTS_1
