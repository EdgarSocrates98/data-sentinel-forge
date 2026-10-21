"""DoctorxSentinel cross-correlation tests (lf-0030, PHASE 8).

Deterministic declared-key correlation: location anchors + category.
Correlation preserves each side's origin, severity, status and confidence;
it is never independent proof, never a status upgrade, never a causal claim.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from data_sentinel.adapters.doctor import DoctorBundleError, import_doctor_bundle
from data_sentinel.cli import app
from data_sentinel.core.contracts import (
    Evidence,
    EvidenceProvenance,
    Finding,
    FindingCategory,
    FindingStatus,
    Severity,
)
from data_sentinel.diagnostics.cross_correlation import (
    DISCLAIMER,
    correlate_findings,
)

RUNNER = CliRunner()


def _doctor_bundle(tmp_path: Path, findings: list[dict]) -> Path:
    p = tmp_path / "doctor.json"
    p.write_text(json.dumps({
        "contract_version": "forge-contracts/1",
        "tool": {"name": "forge-doctor-data", "version": "1.0.3"},
        "findings": findings,
    }), encoding="utf-8")
    return p


def _sentinel_evidence(location: str, *, source: str = "cloudwatch_logs",
                       confidence: float = 0.9) -> Evidence:
    return Evidence(
        source=source,
        source_location=location,
        captured_at=datetime.now(UTC),
        content_hash="h" * 16,
        sanitized_excerpt="runtime signal",
        provenance=EvidenceProvenance.OBSERVED,
        confidence=confidence,
    )


def _sentinel_finding(category: FindingCategory, severity: Severity,
                      status: FindingStatus, ev: Evidence) -> Finding:
    return Finding(
        category=category,
        severity=severity,
        status=status,
        explanation="runtime finding",
        evidence_ids=[ev.evidence_id],
    )


# ---------------------------------------------------------------------------
# Unit — correlate_findings over declared keys
# ---------------------------------------------------------------------------


def test_path_category_correlation(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [{
        "check_id": "SQL001", "message": "select * sem projeção",
        "severity": "high", "confidence": "high", "category": "sql",
        "file": "jobs/etl.py",
    }])
    imported = import_doctor_bundle(bundle)
    ev = _sentinel_evidence("jobs/etl.py:40-52")
    sf = _sentinel_finding(FindingCategory.SQL_ANTIPATTERN, Severity.HIGH,
                           FindingStatus.CONFIRMED, ev)
    report = correlate_findings(imported.findings, imported.evidence, [sf], [ev])
    assert len(report.pairs) == 1
    pair = report.pairs[0]
    assert pair.match_strength == "path+category"
    assert "loc:jobs/etl.py" in pair.matched_keys
    # both origins preserved
    assert pair.doctor_origins == ["forge-doctor-data:1.0.3"]
    assert pair.sentinel_origins == ["cloudwatch_logs"]
    # confidence preserved verbatim per side — never merged
    assert pair.doctor_confidence == pytest.approx(0.8)
    assert pair.sentinel_confidence == pytest.approx(0.9)
    # status preserved — sentinel stays CONFIRMED, doctor stays PROBABLE
    assert pair.doctor_status == "PROBABLE"
    assert pair.sentinel_status == "CONFIRMED"
    assert report.doctor_only == []
    assert report.sentinel_only == []
    assert not report.doctor_absent


def test_correlation_is_not_independent_proof(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [{
        "check_id": "IAM1", "severity": "error", "confidence": "high",
        "category": "iam", "file": "infra/policy.json",
    }])
    imported = import_doctor_bundle(bundle)
    ev = _sentinel_evidence("infra/policy.json:3")
    sf = _sentinel_finding(FindingCategory.PERMISSIONS, Severity.HIGH,
                           FindingStatus.PROBABLE, ev)
    report = correlate_findings(imported.findings, imported.evidence, [sf], [ev])
    assert report.pairs
    assert report.no_confirmation_upgrade is True
    assert report.disclaimer == DISCLAIMER
    assert "independent proof" in report.disclaimer
    assert "causality" in report.disclaimer
    # the doctor finding keeps its imported status — never promoted
    assert imported.findings[0].status == FindingStatus.PROBABLE


def test_no_causality_claim_or_status_merge(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [{
        "check_id": "DQ1", "severity": "warning", "confidence": "low",
        "category": "quality", "file": "dq/checks.py",
    }])
    imported = import_doctor_bundle(bundle)
    assert imported.findings[0].status == FindingStatus.POSSIBLE
    ev = _sentinel_evidence("dq/checks.py:1")
    sf = _sentinel_finding(FindingCategory.DATA_QUALITY, Severity.MEDIUM,
                           FindingStatus.CONFIRMED, ev)
    report = correlate_findings(imported.findings, imported.evidence, [sf], [ev])
    pair = report.pairs[0]
    # POSSIBLE doctor + CONFIRMED sentinel → the pair reports BOTH, unchanged
    assert pair.doctor_status == "POSSIBLE"
    assert pair.sentinel_status == "CONFIRMED"
    # doctor finding object itself untouched
    assert imported.findings[0].status == FindingStatus.POSSIBLE


def test_basename_match_is_weaker_and_marked(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [{
        "check_id": "SQL1", "severity": "low", "confidence": "medium",
        "category": "sql", "file": "etl/join.py",
    }])
    imported = import_doctor_bundle(bundle)
    ev = _sentinel_evidence("other_dir/join.py:9")
    sf = _sentinel_finding(FindingCategory.SQL_ANTIPATTERN, Severity.LOW,
                           FindingStatus.POSSIBLE, ev)
    report = correlate_findings(imported.findings, imported.evidence, [sf], [ev])
    assert len(report.pairs) == 1
    assert report.pairs[0].match_strength == "basename+category"
    assert any("basename" in lim for lim in report.limitations)


def test_path_only_when_categories_differ(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [{
        "check_id": "SEC1", "severity": "high", "confidence": "high",
        "category": "security", "file": "cfg/app.yaml",
    }])
    imported = import_doctor_bundle(bundle)
    ev = _sentinel_evidence("cfg/app.yaml:12")
    sf = _sentinel_finding(FindingCategory.CONFIGURATION, Severity.HIGH,
                           FindingStatus.PROBABLE, ev)
    report = correlate_findings(imported.findings, imported.evidence, [sf], [ev])
    assert len(report.pairs) == 1
    assert report.pairs[0].match_strength == "path-only"
    assert report.pairs[0].matched_keys == ["loc:cfg/app.yaml"]


def test_no_correlation_lists_both_sides(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [{
        "check_id": "X1", "severity": "info", "confidence": "medium",
        "category": "cost", "file": "a/x.py",
    }])
    imported = import_doctor_bundle(bundle)
    ev = _sentinel_evidence("totally/different.py:1")
    sf = _sentinel_finding(FindingCategory.OUT_OF_MEMORY, Severity.HIGH,
                           FindingStatus.CONFIRMED, ev)
    report = correlate_findings(imported.findings, imported.evidence, [sf], [ev])
    assert report.pairs == []
    assert report.doctor_only == [imported.findings[0].finding_id]
    assert report.sentinel_only == [sf.finding_id]


def test_absent_doctor_evidence_clean() -> None:
    ev = _sentinel_evidence("j/x.py:1")
    sf = _sentinel_finding(FindingCategory.OUT_OF_MEMORY, Severity.HIGH,
                           FindingStatus.CONFIRMED, ev)
    report = correlate_findings([], [], [sf], [ev])
    assert report.doctor_absent is True
    assert report.pairs == []
    assert report.sentinel_only == [sf.finding_id]
    assert report.limitations


def test_deterministic_output(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [
        {"check_id": "A", "severity": "low", "confidence": "low",
         "category": "sql", "file": "q/one.py"},
        {"check_id": "B", "severity": "high", "confidence": "high",
         "category": "iam", "file": "q/two.py"},
    ])
    imported = import_doctor_bundle(bundle)
    ev1 = _sentinel_evidence("q/one.py:5")
    ev2 = _sentinel_evidence("q/two.py:5")
    s1 = _sentinel_finding(FindingCategory.SQL_ANTIPATTERN, Severity.LOW,
                           FindingStatus.POSSIBLE, ev1)
    s2 = _sentinel_finding(FindingCategory.PERMISSIONS, Severity.HIGH,
                           FindingStatus.PROBABLE, ev2)
    r1 = correlate_findings(
        imported.findings, imported.evidence, [s1, s2], [ev1, ev2]).to_dict()
    r2 = correlate_findings(
        imported.findings, imported.evidence, [s2, s1], [ev2, ev1]).to_dict()
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
    assert len(r1["pairs"]) == 2


def test_finding_without_evidence_never_correlates(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [{
        "check_id": "N1", "severity": "info", "confidence": "low",
        "category": "sql",
    }])  # no file → source_location is bundle:// — only a bundle anchor
    imported = import_doctor_bundle(bundle)
    ev = _sentinel_evidence("q/one.py:5")
    sf_no_ev = Finding(
        category=FindingCategory.SQL_ANTIPATTERN, severity=Severity.LOW,
        status=FindingStatus.POSSIBLE, explanation="sem evidência")
    report = correlate_findings(
        imported.findings, imported.evidence, [sf_no_ev], [ev])
    # bundle:// producer anchor never matches a real path — no pair
    assert report.pairs == []


def test_correlation_preserves_provenance(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [{
        "check_id": "DEP1", "severity": "medium", "confidence": "medium",
        "category": "dependencies", "file": "requirements/prod.txt",
    }])
    imported = import_doctor_bundle(bundle)
    assert imported.evidence[0].provenance == EvidenceProvenance.DECLARED
    ev = _sentinel_evidence("requirements/prod.txt")
    sf = _sentinel_finding(FindingCategory.DEPENDENCY, Severity.MEDIUM,
                           FindingStatus.PROBABLE, ev)
    report = correlate_findings(imported.findings, imported.evidence, [sf], [ev])
    assert report.pairs[0].doctor_origins == ["forge-doctor-data:1.0.3"]
    assert report.pairs[0].sentinel_origins == ["cloudwatch_logs"]
    assert imported.evidence[0].provenance == EvidenceProvenance.DECLARED
    assert ev.provenance == EvidenceProvenance.OBSERVED


# ---------------------------------------------------------------------------
# CLI + registry surfaces
# ---------------------------------------------------------------------------


def _sentinel_report(tmp_path: Path, findings: list[Finding],
                     evidence: list[Evidence]) -> Path:
    p = tmp_path / "sentinel-report.json"
    p.write_text(json.dumps({
        "report_id": "rep-1",
        "findings": [f.model_dump(mode="json") for f in findings],
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "summary": "", "limitations": [],
    }, default=str), encoding="utf-8")
    return p


def test_cli_import_doctor_bundle_with_correlate(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [{
        "check_id": "SQL9", "severity": "high", "confidence": "high",
        "category": "sql", "file": "job/main.py",
    }])
    ev = _sentinel_evidence("job/main.py:77")
    sf = _sentinel_finding(FindingCategory.SQL_ANTIPATTERN, Severity.HIGH,
                           FindingStatus.CONFIRMED, ev)
    report_file = _sentinel_report(tmp_path, [sf], [ev])
    result = RUNNER.invoke(app, [
        "import", "doctor-bundle", "-f", str(bundle),
        "--correlate", str(report_file), "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    corr = payload["correlation"]
    assert len(corr["pairs"]) == 1
    assert corr["pairs"][0]["match_strength"] == "path+category"
    assert corr["pairs"][0]["doctor"]["status"] == "PROBABLE"
    assert corr["pairs"][0]["sentinel"]["status"] == "CONFIRMED"
    assert corr["no_confirmation_upgrade"] is True


def test_cli_import_correlate_verb(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [{
        "check_id": "C1", "severity": "low", "confidence": "low",
        "category": "cost", "file": "fin/calc.py",
    }])
    ev = _sentinel_evidence("fin/calc.py:2")
    sf = _sentinel_finding(FindingCategory.COST, Severity.LOW,
                           FindingStatus.POSSIBLE, ev)
    report_file = _sentinel_report(tmp_path, [sf], [ev])
    result = RUNNER.invoke(app, [
        "import", "correlate",
        "--doctor", str(bundle), "--sentinel", str(report_file), "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "sentinel/doctor-correlation/v1"
    assert len(payload["pairs"]) == 1
    assert "independent proof" in payload["disclaimer"]
    assert "causality" in payload["disclaimer"]


def test_cli_correlate_absent_doctor_side(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [])  # valid envelope, zero findings
    ev = _sentinel_evidence("x.py:1")
    sf = _sentinel_finding(FindingCategory.COST, Severity.LOW,
                           FindingStatus.POSSIBLE, ev)
    report_file = _sentinel_report(tmp_path, [sf], [ev])
    result = RUNNER.invoke(app, [
        "import", "correlate",
        "--doctor", str(bundle), "--sentinel", str(report_file), "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["doctor_absent"] is True
    assert payload["pairs"] == []
    assert payload["sentinel_only"] == [sf.finding_id]


def test_cli_correlate_rejects_malformed_report(tmp_path: Path) -> None:
    bundle = _doctor_bundle(tmp_path, [])
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"nope": 1}), encoding="utf-8")
    result = RUNNER.invoke(app, [
        "import", "correlate",
        "--doctor", str(bundle), "--sentinel", str(bad), "--json",
    ])
    assert result.exit_code == 1
    assert "findings" in result.output


def test_registry_tool_correlate(tmp_path: Path) -> None:
    from data_sentinel.core.contracts.agent import ToolInvocation
    from data_sentinel.tools.registry import build_default_registry, execute_tool

    bundle = _doctor_bundle(tmp_path, [{
        "check_id": "Q1", "severity": "medium", "confidence": "medium",
        "category": "quality", "file": "dq/rules.py",
    }])
    ev = _sentinel_evidence("dq/rules.py:3")
    sf = _sentinel_finding(FindingCategory.DATA_QUALITY, Severity.MEDIUM,
                           FindingStatus.PROBABLE, ev)
    report_file = _sentinel_report(tmp_path, [sf], [ev])
    registry = build_default_registry()
    desc = registry.get("sentinel.doctor.correlate")
    assert desc.tool_id == "sentinel.doctor.correlate"
    res = execute_tool(ToolInvocation(
        invocation_id="inv-1", tool_id="sentinel.doctor.correlate",
        input={"doctor_bundle": str(bundle), "sentinel_report": str(report_file)},
    ), registry=registry)
    assert res.ok, res.error
    pairs = res.output["pairs"]
    assert len(pairs) == 1
    assert pairs[0]["doctor"]["status"] == "POSSIBLE"  # medium → POSSIBLE
    assert pairs[0]["sentinel"]["status"] == "PROBABLE"
    assert res.output["no_confirmation_upgrade"] is True


def test_load_sentinel_findings_rejects_non_json(tmp_path: Path) -> None:
    from data_sentinel.cli import _load_sentinel_findings

    p = tmp_path / "x.json"
    p.write_text("{broken", encoding="utf-8")
    with pytest.raises(DoctorBundleError):
        _load_sentinel_findings(p)
