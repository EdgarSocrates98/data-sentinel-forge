"""Doctor bundle adapter tests (Cycle 03.1, ds-0033)."""

import json
from pathlib import Path

import pytest

from data_sentinel.adapters.doctor import (
    DoctorBundleError,
    detect_bundle_format,
    import_doctor_bundle,
    load_doctor_file,
)
from data_sentinel.core.contracts import EvidenceProvenance, FindingStatus

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "doctor-data"


def test_import_real_handoff_bundle() -> None:
    r = import_doctor_bundle(FIX / "handoff-real-probe.json")
    assert r.format == "handoff-bundle@1"
    assert len(r.findings) == 73
    assert len(r.evidence) == 73
    assert all(e.provenance == EvidenceProvenance.DECLARED for e in r.evidence)
    assert all(f.status != FindingStatus.CONFIRMED for f in r.findings)
    assert all("importado:forge-doctor-data" in f.explanation for f in r.findings)
    warn = [f for f in r.findings if f.severity.value == "MEDIUM"]
    assert warn  # AWS002/DEP002/PY002/REP002


def test_import_real_scan_json() -> None:
    r = import_doctor_bundle(FIX / "scan-real-probe.json")
    assert r.format == "scan-json@3.0"
    assert len(r.findings) == 73


def test_import_canonical_forge_contracts() -> None:
    r = import_doctor_bundle(
        Path(__file__).resolve().parents[2] / "fixtures" / "doctor-api"
        / "forge-contracts-1-handoff.json"
    )
    assert r.format == "forge-contracts/1"
    assert r.bundle.producer.name
    assert len(r.findings) == 1
    # fixture canônico não traz confidence → UNKNOWN (nunca auto-CONFIRMED)
    assert r.findings[0].status == FindingStatus.UNKNOWN


def test_reject_malformed_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(DoctorBundleError, match="malformed"):
        import_doctor_bundle(p)


def test_reject_unrecognized_shape(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    with pytest.raises(DoctorBundleError, match="unrecognized"):
        import_doctor_bundle(p)


def test_reject_non_dict(tmp_path: Path) -> None:
    p = tmp_path / "arr.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    with pytest.raises(DoctorBundleError, match="object"):
        import_doctor_bundle(p)


def test_reject_oversized(tmp_path: Path) -> None:
    from data_sentinel.adapters.doctor import adapter
    p = tmp_path / "big.json"
    p.write_bytes(b'{"results": ["' + b"A" * (adapter.MAX_BUNDLE_BYTES) + b'"]}')
    with pytest.raises(DoctorBundleError, match="exceeds"):
        import_doctor_bundle(p)


def test_missing_file() -> None:
    with pytest.raises(DoctorBundleError, match="not a file"):
        import_doctor_bundle(Path("/nonexistent/bundle.json"))


def test_secrets_redacted(tmp_path: Path) -> None:
    p = tmp_path / "sec.json"
    p.write_text(json.dumps({
        "contract": "handoff-bundle",
        "contract_version": 1,
        "tool": {"name": "forge-doctor-data", "version": "1.0.3"},
        "results": [{
            "check_id": "X1",
            "message": "aws_secret_access_key=AKIAIOSFODNN7EXAMPLE exposto",
            "severity": "error", "confidence": "high",
            "file": "cfg.py",
        }],
        "graph": {"entities": [], "relationships": []},
        "capabilities": {}, "plans": [],
        "project": {}, "summary": {},
    }), encoding="utf-8")
    r = import_doctor_bundle(p)
    blob = r.findings[0].explanation + r.evidence[0].sanitized_excerpt
    assert "AKIAIOSFODNN7EXAMPLE" not in blob


def test_unknown_confidence_maps_to_unknown_status(tmp_path: Path) -> None:
    p = tmp_path / "u.json"
    p.write_text(json.dumps({
        "contract_version": "forge-contracts/1",
        "tool": {"name": "forge-doctor-api", "version": "0.2.3"},
        "findings": [{
            "id": "OAS001", "description": "spec ambígua",
            "severity": "HIGH", "confidence": "UNKNOWN",
            "unknowns": [{"subject": "s", "missing": "m"}],
        }],
    }), encoding="utf-8")
    r = import_doctor_bundle(p)
    assert r.findings[0].status == FindingStatus.UNKNOWN
    assert "desconhecidos: 1" in r.findings[0].explanation


def test_detect_all_formats() -> None:
    assert detect_bundle_format(
        {"contract": "handoff-bundle", "results": []}) == "handoff-bundle@1"
    assert detect_bundle_format(
        {"contract_version": "forge-contracts/1", "findings": []}
    ) == "forge-contracts/1"
    assert detect_bundle_format(
        {"schema_version": "3.0", "results": []}) == "scan-json@3.0"


def test_empty_bundle_file_rejected(tmp_path: Path) -> None:
    p = tmp_path / "e.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(DoctorBundleError, match="empty"):
        load_doctor_file(p)


def test_bundle_content_never_executed(tmp_path: Path) -> None:
    """A finding containing code-shaped text must import as text only."""
    p = tmp_path / "code.json"
    p.write_text(json.dumps({
        "contract_version": "forge-contracts/1",
        "tool": {"name": "forge-doctor-data"},
        "findings": [{
            "check_id": "EVIL1",
            "message": "__import__('os').system('touch /tmp/pwned-marker')",
            "severity": "info", "confidence": "low",
        }],
    }))
    r = import_doctor_bundle(p)
    assert len(r.findings) == 1
    assert not Path("/tmp/pwned-marker").exists()  # noqa: S108 - marcador de não-execução
