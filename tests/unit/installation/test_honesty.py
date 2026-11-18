"""wave-10 honesty tests — a failed mandatory component can never ride
on a PASS verification, a "completed" registry write or a PASS receipt.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from data_sentinel import _forgecontext as fctx
from data_sentinel.cli import app
from data_sentinel.installation import service

runner = CliRunner()


def test_context_register_failure_is_not_false_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_register_context BLOCKED → receipt failed + verification FAIL and
    no ``~/.forge/installations/`` manifest claiming an install."""
    fake_home = tmp_path / "forge-home"
    monkeypatch.setenv("FORGE_HOME_OVERRIDE", str(fake_home))
    root = tmp_path / "proj"
    root.mkdir()

    def _boom(*args, **kwargs):
        raise fctx.ContextError("FORGE-CONTEXT-TEST", "forced failure")

    monkeypatch.setattr(fctx, "install_transaction", _boom)

    receipt = service.install(host="claude", scope="project", root=root, yes=True)
    assert receipt["status"] == "failed"
    assert receipt["verification"]["status"] == "FAIL"
    assert any(
        c["id"] == "context-registry" and c["status"] == "BLOCKED" for c in receipt["checks"]
    )
    # The registry must not claim a forge whose mandatory context
    # registration failed.
    assert not (fake_home / ".forge" / "installations" / "data-sentinel-forge.json").exists()


def test_context_register_failure_cli_exit_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "forge-home"
    monkeypatch.setenv("FORGE_HOME_OVERRIDE", str(fake_home))
    root = tmp_path / "proj"
    root.mkdir()

    def _boom(*args, **kwargs):
        raise fctx.ContextError("FORGE-CONTEXT-TEST", "forced failure")

    monkeypatch.setattr(fctx, "install_transaction", _boom)

    result = runner.invoke(
        app,
        [
            "install",
            "--scope",
            "project",
            "--root",
            str(root),
            "--host",
            "claude",
            "--yes",
            "--json",
        ],
    )
    assert result.exit_code == 1
    doc = json.loads(result.output)
    assert doc["status"] == "failed"
    assert doc["verification"]["status"] == "FAIL"


def test_install_receipt_verification_matches_checks(tmp_path: Path, monkeypatch) -> None:
    """A completed install keeps verification PASS only when every check
    is PASS/NOT_APPLICABLE — the recomputed field must agree."""
    monkeypatch.setenv("FORGE_HOME_OVERRIDE", str(tmp_path / "forge-home"))
    root = tmp_path / "proj"
    root.mkdir()
    receipt = service.install(host="claude", scope="project", root=root, yes=True)
    assert receipt["status"] == "completed"
    expected = "PASS" if all(
        c["status"] in ("PASS", "NOT_APPLICABLE") for c in receipt["checks"]
    ) else "FAIL"
    assert receipt["verification"]["status"] == expected


def test_gateway_profile_flag_accepted(tmp_path: Path, monkeypatch) -> None:
    """``--gateway-profile`` is the canonical flag the orchestrator sends;
    ``--gateway`` stays a working alias."""
    monkeypatch.setenv("FORGE_HOME_OVERRIDE", str(tmp_path / "forge-home"))
    root = tmp_path / "proj"
    root.mkdir()
    result = runner.invoke(
        app,
        [
            "install",
            "--scope",
            "project",
            "--root",
            str(root),
            "--host",
            "claude",
            "--gateway-profile",
            "deep",
            "--yes",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    doc = json.loads(result.output)
    assert doc["status"] == "completed"


def test_gateway_alias_still_accepted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_HOME_OVERRIDE", str(tmp_path / "forge-home"))
    root = tmp_path / "proj"
    root.mkdir()
    result = runner.invoke(
        app,
        [
            "install",
            "--scope",
            "project",
            "--root",
            str(root),
            "--host",
            "claude",
            "--gateway",
            "economy",
            "--yes",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output


def test_interactive_confirm_defaults_to_no(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bare Enter on the apply/confirm prompts must DECLINE — an
    approval gate that defaults to yes is no gate at all."""
    from data_sentinel.ui import kit as uikit
    from data_sentinel.ui.kit import UIContext

    ctx = UIContext(interactive=True, color=False, unicode=False, width=80, ansi=False)
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    assert uikit.confirm("apply?", ctx=ctx) is False
    # approve_plan renders then confirms — same default-False contract.
    monkeypatch.setattr(uikit.sys.stdout, "write", lambda s: 0)
    assert uikit.approve_plan({"status": "planned", "planned_files": []}, ctx=ctx) is False


def test_register_propagates_declared_install_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``~/.forge/installations/`` carries the install-2.1 declared
    surface verbatim from forge.json."""
    fake_home = tmp_path / "forge-home"
    monkeypatch.setenv("FORGE_HOME_OVERRIDE", str(fake_home))
    root = tmp_path / "proj"
    root.mkdir()
    service.install(host="claude", scope="project", root=root, yes=True)
    doc = json.loads(
        (fake_home / ".forge" / "installations" / "data-sentinel-forge.json").read_text()
    )
    assert doc["installation_kind"] == "content"
    assert doc["depends_on"] == []
    surf = doc["install"]
    assert "mcp-verify" in surf["operations"] and "update" not in surf["operations"]
    assert "--gateway-profile" in surf["flags"]
    assert surf["approval"] == "--yes"
    assert doc["mcp"]["verify_tool"] == "sentinel.status"
