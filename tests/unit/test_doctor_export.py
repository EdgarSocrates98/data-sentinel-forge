"""Doctor export tests (ds-0046) — round-trip with real adapter."""

import json
from datetime import UTC, datetime
from pathlib import Path

from data_sentinel.adapters.doctor.adapter import detect_bundle_format, import_doctor_bundle
from data_sentinel.adapters.doctor.exporter import export_report
from data_sentinel.core.contracts import (
    DiagnosticReport,
    Finding,
    FindingCategory,
    FindingStatus,
    Severity,
)


def _report() -> DiagnosticReport:
    return DiagnosticReport(
        request_id="r1",
        created_at=datetime(2026, 10, 20, tzinfo=UTC),
        findings=[Finding(
            category=FindingCategory.DATA_QUALITY,
            severity=Severity.HIGH,
            status=FindingStatus.CONFIRMED,
            explanation="drift confirmado em 'amount' (KS p=0.003)",
            evidence_ids=["drift:amount:ks_pvalue"],
            recommendations=["comparar baseline"])],
        limitations=["somente observações exportadas"])


def test_export_shape() -> None:
    b = export_report(_report(), source_ref="marquez-run-1")
    assert b.contract_version == "forge-contracts/1"
    assert b.producer.name == "data-sentinel"
    assert len(b.findings) == 1
    f = b.findings[0]
    assert f.confidence == "CONFIRMED"  # verbatim
    assert f.check_id == "sentinel-0"
    assert f.fingerprint
    assert b.integrity and b.integrity.content_sha256
    assert b.summary["finding_count"] == 1


def test_export_import_roundtrip(tmp_path: Path) -> None:
    """Sentinel export must be importable by the Sentinel Doctor adapter."""
    b = export_report(_report())
    p = tmp_path / "sentinel-bundle.json"
    p.write_text(b.model_dump_json(), encoding="utf-8")
    fmt = detect_bundle_format(json.loads(p.read_text(encoding="utf-8")))
    imported = import_doctor_bundle(p)
    assert fmt
    assert len(imported.findings) == 1
    imp_f = imported.findings[0]
    assert "drift" in imp_f.explanation


def test_export_serialization_stable() -> None:
    r = _report()
    b1 = export_report(r)
    b2 = export_report(r)
    assert b1.model_dump_json() != ""
    # integrity hash deterministic for same content
    j1 = json.loads(b1.model_dump_json())
    j2 = json.loads(b2.model_dump_json())
    assert j1["integrity"]["content_sha256"] == j2["integrity"][
        "content_sha256"]
