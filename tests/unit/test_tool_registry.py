"""Tool registry tests (ds-0052)."""

import json
from pathlib import Path

import pytest

from data_sentinel.core.contracts.agent import ToolDescriptor, ToolInvocation, ToolPermission
from data_sentinel.tools import ToolUnavailableError, build_default_registry, execute_tool

FIX = Path(__file__).parent.parent / "fixtures"


def _inv(tid: str, **inp) -> ToolInvocation:
    return ToolInvocation(invocation_id="t1", tool_id=tid, input=inp)


def test_registry_lists_real_tools() -> None:
    r = build_default_registry()
    ids = [t.tool_id for t in r.list_tools()]
    assert "sentinel.spark.analyze_plan" in ids
    assert "sentinel.lineage.impact" in ids
    assert len(ids) >= 16
    for t in r.list_tools():
        assert t.version and t.input_schema and t.permissions


def test_blocked_permissions_never_registered() -> None:
    r = build_default_registry()
    with pytest.raises(ToolUnavailableError):
        r.register(ToolDescriptor(
            tool_id="evil.delete", name="x",
            permissions=[ToolPermission.DESTRUCTIVE]))
    with pytest.raises(ToolUnavailableError):
        r.register(ToolDescriptor(
            tool_id="evil.cloudwrite", name="x",
            permissions=[ToolPermission.CLOUD_WRITE]))


def test_unknown_tool_fails_cleanly() -> None:
    res = execute_tool(_inv("sentinel.nope"))
    assert not res.ok and "desconhecida" in res.error


def test_sql_analyze_tool_real(tmp_path: Path) -> None:
    q = tmp_path / "q.sql"
    q.write_text("SELECT * FROM a JOIN b ON a.id = b.id", encoding="utf-8")
    res = execute_tool(_inv("sentinel.sql.analyze", file=str(q)))
    assert res.ok, res.error
    assert res.output["findings"] is not None
    assert res.output["report_id"]


def test_lineage_ingest_tool() -> None:
    res = execute_tool(_inv("sentinel.lineage.ingest",
                            file=str(FIX / "lineage/marquez-real.jsonl")))
    assert res.ok
    assert res.output["events"] == 4
    assert res.output["downstream"]


def test_quality_assess_tool() -> None:
    res = execute_tool(_inv(
        "sentinel.quality.assess",
        file=str(FIX / "quality/pydeequ_metrics.json"),
        adapter="pydeequ"))
    assert res.ok and res.output["count"] == 4


def test_lineage_impact_tool() -> None:
    res = execute_tool(_inv(
        "sentinel.lineage.impact",
        file=str(FIX / "lineage/marquez-real.jsonl"),
        target="s3://lakehouse-raw/raw/events"))
    assert res.ok
    assert res.output["potential_only"] is True
    assert len(res.output["downstream"]) == 2


def test_detect_drift_tool(tmp_path: Path) -> None:
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps([0.0] * 50), encoding="utf-8")
    c.write_text(json.dumps([5.0] * 50), encoding="utf-8")
    res = execute_tool(_inv("sentinel.quality.detect_drift",
                            baseline_file=str(b), current_file=str(c)))
    assert res.ok
    assert res.output["drift"]["level"] in ("medium", "high")


def test_dry_run() -> None:
    res = execute_tool(_inv("sentinel.sql.analyze", file="/x"),
                       dry_run=True)
    assert res.ok and res.output["dry_run"] is True


def test_doctor_import_tool(tmp_path: Path) -> None:
    bundle = tmp_path / "b.json"
    bundle.write_text(json.dumps({
        "schema_version": "1.0.0",
        "producer": {"name": "forge-doctor-data", "version": "1.0.3"},
        "findings": [{"check_id": "c1", "message": "issue",
                      "severity": "high"}]}), encoding="utf-8")
    res = execute_tool(_inv("sentinel.doctor.import_bundle",
                            file=str(bundle)))
    assert res.ok
    assert len(res.output["findings"]) == 1
