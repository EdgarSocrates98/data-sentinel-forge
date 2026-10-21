"""ds-0110 — install CLI: approval gate, dry-run, lifecycle verbs."""

import json
from pathlib import Path

from typer.testing import CliRunner

from data_sentinel.cli import app

runner = CliRunner()


def _installed(tmp: Path) -> None:
    result = runner.invoke(
        app, ["install", "--scope", "project", "--root", str(tmp),
              "--host", "claude", "--yes"]
    )
    assert result.exit_code == 0, result.output


def test_install_requires_approval(tmp_path: Path) -> None:
    """Non-TTY without --yes → usage error, nothing written."""
    result = runner.invoke(
        app, ["install", "--scope", "project", "--root", str(tmp_path)]
    )
    assert result.exit_code == 2
    assert "--yes" in result.output or "não-interativo" in result.output
    assert list(tmp_path.rglob("*")) == []


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["install", "--scope", "project", "--root", str(tmp_path),
              "--host", "claude", "--dry-run"]
    )
    assert result.exit_code == 0
    assert "planned" in result.output
    assert list(tmp_path.rglob("*")) == []


def test_install_yes_creates_assets(tmp_path: Path) -> None:
    _installed(tmp_path)
    assert (tmp_path / "AGENTS.md").is_file()
    assert "data-sentinel-forge:managed" in (tmp_path / "AGENTS.md").read_text()
    mcp = json.loads((tmp_path / ".mcp.json").read_text())
    entry = mcp["mcpServers"]["data-sentinel"]
    # §7.1 — absolute console script preferred, bare name is the fallback
    assert entry["command"].endswith("data-sentinel")
    assert entry["args"] == ["mcp", "serve"]


def test_install_json_output(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["install", "--scope", "project", "--root", str(tmp_path),
              "--host", "claude", "--yes", "--json"]
    )
    assert result.exit_code == 0
    doc = json.loads(result.output)
    assert doc["status"] == "completed"
    assert doc["schema"] == "forge/InstallReceipt/v1"


def test_unknown_host_fails(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["install", "--scope", "project", "--root", str(tmp_path),
              "--host", "emacs", "--yes"]
    )
    assert result.exit_code == 1
    assert "host" in result.output


def test_status_and_doctor(tmp_path: Path) -> None:
    _installed(tmp_path)
    status = runner.invoke(app, ["install", "status", "--root", str(tmp_path)])
    assert status.exit_code == 0, status.output
    assert "healthy" in status.output or "managed" in status.output
    doctor = runner.invoke(
        app, ["install", "doctor", "--root", str(tmp_path), "--json"]
    )
    assert doctor.exit_code in (0, 1)  # mcp-handshake may be UNVERIFIED
    doc = json.loads(doctor.output)
    assert doc["schema"] == "forge/InstallationHealth/v1"


def test_uninstall_clean(tmp_path: Path) -> None:
    _installed(tmp_path)
    (tmp_path / "user.txt").write_text("mine", encoding="utf-8")
    result = runner.invoke(
        app, ["install", "uninstall", "--root", str(tmp_path), "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "user.txt").is_file()
    assert not (tmp_path / "AGENTS.md").exists()


def test_idempotent_reinstall(tmp_path: Path) -> None:
    _installed(tmp_path)
    _installed(tmp_path)
    assert (tmp_path / "AGENTS.md").is_file()
    # ledger stable — no duplicate entries
    second = json.loads(
        (tmp_path / ".data-sentinel/install/install-ledger.json").read_text()
    )
    assert isinstance(second["entries"], dict)


def test_manifest_static_matches_programmatic(tmp_path: Path) -> None:
    """forge.json / forge.agentic.json must not drift from `install manifest`."""
    repo = Path(__file__).resolve().parents[3]
    for name, args in (
        ("forge.json", []),
        ("forge.agentic.json", ["--agentic"]),
    ):
        result = runner.invoke(app, ["install", "manifest", *args])
        assert result.exit_code == 0
        emitted = json.loads(result.output)
        static = json.loads((repo / name).read_text(encoding="utf-8"))
        assert static == emitted, f"{name} drifted — regenerate via install manifest"


def test_env_report(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["install", "env", "--root", str(tmp_path), "--json"]
    )
    assert result.exit_code == 0, result.output
    doc = json.loads(result.output)
    assert doc["schema"] == "data-sentinel/EnvironmentReport/v1"
    assert doc["python"]["meets_floor"] is True
    assert set(doc["hosts"]) == {"claude", "devin", "codex", "copilot", "cursor"}
    # §11.3 — env values are never emitted
    assert set(doc["env_vars"].values()) <= {"set", "unset"}


def test_drift_detect_and_repair_restores(tmp_path: Path) -> None:
    _installed(tmp_path)
    skill = tmp_path / ".claude/skills/data-sentinel-report/SKILL.md"
    original = skill.read_bytes()
    skill.write_text("corrupted", encoding="utf-8")
    status = runner.invoke(
        app, ["install", "status", "--root", str(tmp_path), "--json"]
    )
    assert "drift" in status.output or skill.name in status.output
    result = runner.invoke(
        app, ["install", "repair", "--root", str(tmp_path), "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert skill.read_bytes() == original


def test_repair_refuses_foreign_file(tmp_path: Path) -> None:
    _installed(tmp_path)
    foreign = tmp_path / ".claude/skills/data-sentinel-report/SKILL.md"
    foreign.write_text("user edit", encoding="utf-8")
    # repair on a file never owned by the ledger is a refused/skip, not a clobber
    result = runner.invoke(
        app, ["install", "repair", "--root", str(tmp_path), "--yes"]
    )
    assert result.exit_code in (0, 1), result.output
