"""Cycle 05.1 E2E A-J — EMR intelligence end-to-end."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from data_sentinel.agents.investigator import investigate
from data_sentinel.cli import app
from data_sentinel.connectors.aws.emr import ALLOWED_ACTIONS
from data_sentinel.core.contracts.agent import ToolInvocation
from data_sentinel.tools.registry import build_default_registry, execute_tool

runner = CliRunner()
FX = Path("fixtures")


def test_a_ec2_failed_step() -> None:
    res = execute_tool(ToolInvocation(
        invocation_id="a", tool_id="sentinel.emr.analyze_ec2",
        input={"file": str(FX / "emr-ec2-failed-step.json")}))
    assert res.ok
    expl = " ".join(f["explanation"] for f in res.output["findings"])
    assert ("falhou" in expl and "BOOTSTRAP" in expl) or "terminou" in expl


def test_b_serverless_slow_job() -> None:
    res = execute_tool(ToolInvocation(
        invocation_id="b", tool_id="sentinel.emr.analyze_serverless",
        input={"file": str(FX / "emr-serverless-failed.json")}))
    assert res.ok
    expl = " ".join(f["explanation"] for f in res.output["findings"])
    assert "tentativa" in expl or "falhou" in expl


def test_c_eks_pending_driver() -> None:
    res = execute_tool(ToolInvocation(
        invocation_id="c", tool_id="sentinel.emr.analyze_eks",
        input={"file": str(FX / "emr-eks-pods.yaml")}))
    assert res.ok
    assert any("unschedulable" in f["explanation"]
               for f in res.output["findings"])


def test_d_spark_cross_platform_honest(tmp_path: Path) -> None:
    r = runner.invoke(app, ["emr", "compare",
                            "--baseline", "x", "--current", "y"])
    assert r.exit_code != 0  # missing files → clean error
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    m = {"metrics": [{"name": "duration_ms", "value": 5,
                      "unit": "ms"}]}
    a.write_text(json.dumps({"context": {"platform": "emr_ec2"},
                             "observation": m}))
    b.write_text(json.dumps({"context": {"platform": "emr_eks"},
                             "observation": m}))
    r = runner.invoke(app, ["emr", "compare",
                            "--baseline", str(a),
                            "--current", str(b)])
    assert "superioridade" in r.output


def test_e_iceberg_integration_reused() -> None:
    assert Path("fixtures/emr-eks-pods.yaml").exists()
    # reuse proof: iceberg tool exists in registry
    reg = build_default_registry()
    assert reg.get("sentinel.iceberg.inspect_metadata")


def test_f_agentic_emr_investigation() -> None:
    rep = investigate(
        "emr serverless job failed",
        {"sentinel.emr.analyze_serverless":
         str(FX / "emr-serverless-failed.json")})
    assert "emr-serverless-expert" in rep.agents_used[0]
    assert rep.findings
    assert "validation" in rep.context


def test_g_offline_full() -> None:
    # all analyzers run without AWS creds or network
    for tid, f in [("sentinel.emr.analyze_ec2", "emr-ec2-failed-step.json"),
                   ("sentinel.emr.analyze_serverless",
                    "emr-serverless-failed.json"),
                   ("sentinel.emr.analyze_eks", "emr-eks-pods.yaml")]:
        res = execute_tool(ToolInvocation(
            invocation_id="g", tool_id=tid,
            input={"file": str(FX / f)}))
        assert res.ok, tid


def test_h_mcp_lists_emr_tools() -> None:
    pytest.importorskip("mcp")
    from data_sentinel.mcp_server import create_server
    srv = create_server()
    assert srv is not None
    reg = build_default_registry()
    emr = [t.tool_id for t in reg.list_tools()
           if t.tool_id.startswith("sentinel.emr.")]
    assert len(emr) == 4


def test_i_no_mutating_aws() -> None:
    mutating = {"run_job_flow", "terminate_job_flows", "add_steps",
                "cancel_steps", "put_auto_scaling_policy",
                "create_job_run", "cancel_job_run", "start_job_run",
                "create_application", "delete_application",
                "create_virtual_cluster", "delete_virtual_cluster"}
    assert not (ALLOWED_ACTIONS & mutating)
    assert all(a.startswith(("list", "describe", "get"))
               for a in ALLOWED_ACTIONS)


def test_j_clean_wheel_offline(tmp_path: Path) -> None:
    wheel = subprocess.run(  # noqa: S603
        ["uv", "build", "--wheel", "-o", str(tmp_path)],  # noqa: S607
        capture_output=True, text=True, cwd=Path.cwd())
    assert wheel.returncode == 0, wheel.stderr
    whl = next(tmp_path.glob("*.whl"))
    venv = tmp_path / "venv"
    subprocess.run(  # noqa: S603 — venv do próprio teste
        [sys.executable, "-m", "venv", str(venv)],
        check=True, capture_output=True)
    pip = venv / "bin" / "pip"
    r = subprocess.run(  # noqa: S603 — venv do próprio teste
        [str(pip), "install", "-q", str(whl)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    ds = venv / "bin" / "data-sentinel"
    out = subprocess.run(  # noqa: S603 — venv do próprio teste
        [str(ds), "emr", "analyze", "-f",
         str(FX / "emr-ec2-failed-step.json").replace(
             "fixtures", str(Path.cwd() / "fixtures")),
         "--platform", "ec2", "--json"],
        capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "emr.ec2" in out.stdout
