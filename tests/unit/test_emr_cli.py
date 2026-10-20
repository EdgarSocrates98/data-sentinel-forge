"""EMR CLI tests (ds-0067)."""

import json
from pathlib import Path

from typer.testing import CliRunner

from data_sentinel.cli import app

runner = CliRunner()
FX = Path(__file__).parent.parent / "fixtures" / "emr-ec2-failed-step.json"


def test_emr_analyze_ec2() -> None:
    r = runner.invoke(app, ["emr", "analyze", "-f", str(FX),
                            "--platform", "ec2", "--json"])
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["analyzer"] == "emr.ec2"
    assert any("falhou" in f["explanation"] or "terminou" in
               f["explanation"] for f in out["findings"])


def test_emr_analyze_bad_platform() -> None:
    r = runner.invoke(app, ["emr", "analyze", "-f", str(FX),
                            "--platform", "gcp"])
    assert r.exit_code == 2


def test_emr_cost_estimated() -> None:
    r = runner.invoke(app, ["emr", "cost", "--platform", "serverless",
                            "--vcpu-hours", "10", "--json"])
    assert r.exit_code == 0
    out = json.loads(r.output)
    assert out["amount"] and out["confidence"] == "POSSIBLE"


def test_emr_cost_unknown_honest() -> None:
    r = runner.invoke(app, ["emr", "cost", "--platform", "serverless"])
    assert "UNKNOWN" in r.output


def test_emr_compare(tmp_path: Path) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({
        "context": {"platform": "emr_ec2", "spark_version": "3.5"},
        "observation": {"metrics": [
            {"name": "duration_ms", "value": 100, "unit": "ms"}]}}), encoding="utf-8")
    b.write_text(json.dumps({
        "context": {"platform": "emr_serverless",
                    "spark_version": "3.4"},
        "observation": {"metrics": [
            {"name": "duration_ms", "value": 80, "unit": "ms"}]}}), encoding="utf-8")
    r = runner.invoke(app, ["emr", "compare",
                            "--baseline", str(a),
                            "--current", str(b), "--json"])
    assert r.exit_code == 0
    assert "superioridade" in r.output or "comparação" in r.output
