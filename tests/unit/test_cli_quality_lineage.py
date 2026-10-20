"""CLI tests for quality/lineage/export commands (ds-0047)."""

import json
from pathlib import Path

from typer.testing import CliRunner

from data_sentinel.cli import app

FIX = Path(__file__).parent.parent / "fixtures"
runner = CliRunner()


def test_quality_validate_ok(tmp_path: Path) -> None:
    c = tmp_path / "c.yaml"
    c.write_text('contract_version: "1.0"\ndataset: a.b\n'
                 'rules:\n - {id: r1, type: completeness, column: x}\n')
    r = runner.invoke(app, ["quality", "validate", "--file", str(c)])
    assert r.exit_code == 0
    assert "OK" in r.output


def test_quality_validate_bad_type(tmp_path: Path) -> None:
    c = tmp_path / "bad.yaml"
    c.write_text("dataset: a.b\nrules:\n - {id: x, type: telepathy}\n")
    r = runner.invoke(app, ["quality", "validate", "--file", str(c)])
    assert r.exit_code == 1
    assert "desconhecido" in r.output


def test_quality_import_json() -> None:
    r = runner.invoke(app, ["quality", "import",
                            "--file", str(FIX / "quality/ge_result.json"),
                            "--adapter", "great_expectations",
                            "--json"])
    assert r.exit_code == 0
    data = json.loads(r.output)
    assert data["count"] == 2
    assert data["observations"][1]["status"] == "FAIL"


def test_lineage_ingest() -> None:
    r = runner.invoke(app, ["lineage", "ingest",
                            "--file", str(FIX / "lineage/marquez-real.jsonl")])
    assert r.exit_code == 0
    assert "4 eventos" in r.output
    assert "->" in r.output


def test_lineage_impact_potential() -> None:
    r = runner.invoke(app, ["lineage", "impact",
                            "--file", str(FIX / "lineage/marquez-real.jsonl"),
                            "--target", "s3://lakehouse-raw/raw/events"])
    assert r.exit_code == 0
    assert "POTENCIAL" in r.output
    assert "marts/daily_revenue" in r.output


def test_report_export_bundle(tmp_path: Path) -> None:
    report = tmp_path / "r.json"
    report.write_text(json.dumps({
        "request_id": "x", "created_at": "2026-10-20T00:00:00Z",
        "findings": []}))
    out = tmp_path / "b.json"
    r = runner.invoke(app, ["report", "export",
                            "--file", str(report), "--output", str(out)])
    assert r.exit_code == 0
    bundle = json.loads(out.read_text())
    assert bundle["contract_version"] == "forge-contracts/1"
    assert bundle["integrity"]["content_sha256"]
