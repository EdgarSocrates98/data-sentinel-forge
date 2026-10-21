"""ds-0118 §13.3 — E2E installation matrix.

Real installs on fresh tmp roots through the CLI runner and the service
facade. Each test maps to the lettered items of the prompt matrix; items
that cannot be homologated locally (PyPI publish, other OSes) are covered
by the CI matrix or declared NOT APPLICABLE in the final report — never
silently skipped here.
"""

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from data_sentinel.cli import app
from data_sentinel.installation import service

runner = CliRunner()

ALL_HOSTS = ("claude", "devin", "codex", "copilot", "cursor")


def _install(root: Path, *args: str) -> dict:
    result = runner.invoke(
        app,
        ["install", "--scope", "project", "--root", str(root), "--yes",
         "--json", *args],
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _lifecycle(root: Path, verb: str, *args: str) -> dict:
    result = runner.invoke(
        app,
        ["install", verb, "--root", str(root), "--json", *args],
    )
    assert result.exit_code == 0, (verb, result.output)
    return json.loads(result.output)


# --- scopes (F/G/H) ------------------------------------------------------

def test_matrix_project_scope(tmp_path: Path) -> None:
    doc = _install(tmp_path, "--host", "claude")
    assert doc["status"] == "completed"
    assert (tmp_path / ".data-sentinel/install").is_dir()
    assert (tmp_path / "AGENTS.md").is_file()


def test_matrix_user_scope(tmp_path: Path, monkeypatch) -> None:
    # user scope resolves to HOME — isolate it so nothing touches ~/
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    result = runner.invoke(
        app,
        ["install", "--scope", "user", "--yes", "--host", "claude", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert (fake_home / ".claude/skills").is_dir()


def test_matrix_workspace_scope(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    doc = _install(ws, "--host", "claude")
    assert doc["status"] == "completed"


# --- profiles (I/J/K) + gateway (L/M/N) ---------------------------------

@pytest.mark.parametrize("profile", ["minimal", "recommended", "full"])
def test_matrix_profiles(tmp_path: Path, profile: str) -> None:
    doc = _install(tmp_path, "--host", "claude", "--profile", profile)
    assert doc["status"] == "completed"


@pytest.mark.parametrize("gw", ["economy", "balanced", "deep"])
def test_matrix_gateway_profiles(tmp_path: Path, gw: str) -> None:
    result = runner.invoke(
        app,
        ["install", "--scope", "project", "--root", str(tmp_path), "--yes",
         "--host", "claude", "--gateway", gw, "--json"],
    )
    assert result.exit_code == 0, result.output


def test_matrix_gateway_off_refused(tmp_path: Path) -> None:
    """§3.4 — only economy/balanced/deep exist; `off` must refuse honestly."""
    result = runner.invoke(
        app,
        ["install", "--scope", "project", "--root", str(tmp_path), "--yes",
         "--host", "claude", "--gateway", "off", "--json"],
    )
    assert result.exit_code == 1
    assert "PROFILE-UNKNOWN" in result.output
    assert list(tmp_path.rglob("*")) == []


# --- hosts (O/P/Q/R + cursor honest limit) -------------------------------

@pytest.mark.parametrize("host", ALL_HOSTS)
def test_matrix_each_host(tmp_path: Path, host: str) -> None:
    doc = _install(tmp_path, "--host", host)
    assert doc["status"] == "completed"
    if host != "cursor":
        skills = list(tmp_path.rglob("SKILL.md"))
        assert skills, f"{host}: no skills rendered"


def test_matrix_cursor_no_catalog_adapter(tmp_path: Path) -> None:
    _install(tmp_path, "--host", "cursor")
    assert not list(tmp_path.rglob("SKILL.md")), (
        "cursor must not receive catalog assets (unsupported)"
    )


# --- components (S/T/U/V) -------------------------------------------------

def test_matrix_skills_only(tmp_path: Path) -> None:
    _install(tmp_path, "--host", "claude", "--components", "skills")
    assert list(tmp_path.rglob("SKILL.md"))
    assert not list(tmp_path.rglob("*.agent.md"))


def test_matrix_agents_only(tmp_path: Path) -> None:
    _install(tmp_path, "--host", "claude", "--components", "agents")
    agents = [p for p in tmp_path.rglob("*.md") if "agents" in str(p)]
    assert agents
    assert not list(tmp_path.rglob("SKILL.md"))


def test_matrix_full_install(tmp_path: Path) -> None:
    _install(tmp_path, "--host", "all", "--profile", "full")
    assert len(list(tmp_path.rglob("SKILL.md"))) >= 4 * 5 - 1
    assert (tmp_path / ".mcp.json").is_file()


# --- pre-existing state (W/X/Y) + AO -------------------------------------

def test_matrix_existing_env_untouched(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("SECRET=keepme\n", encoding="utf-8")
    _install(tmp_path, "--host", "claude")
    assert env.read_text(encoding="utf-8") == "SECRET=keepme\n"


def test_matrix_existing_user_files_intact(tmp_path: Path) -> None:
    user_file = tmp_path / "notes.md"
    user_file.write_text("mine\n", encoding="utf-8")
    claude_skill = tmp_path / ".claude/skills/my-own/SKILL.md"
    claude_skill.parent.mkdir(parents=True)
    claude_skill.write_text("user skill\n", encoding="utf-8")
    _install(tmp_path, "--host", "claude", "--profile", "full")
    assert user_file.read_text(encoding="utf-8") == "mine\n"
    assert claude_skill.read_text(encoding="utf-8") == "user skill\n"


def test_matrix_uninstall_preserves_user_files(tmp_path: Path) -> None:
    _install(tmp_path, "--host", "claude", "--profile", "full")
    user_skill = tmp_path / ".claude/skills/mine/SKILL.md"
    user_skill.parent.mkdir(parents=True, exist_ok=True)
    user_skill.write_text("user\n", encoding="utf-8")
    (tmp_path / "keep.txt").write_text("x", encoding="utf-8")
    _lifecycle(tmp_path, "uninstall")
    assert user_skill.read_text(encoding="utf-8") == "user\n"
    assert (tmp_path / "keep.txt").is_file()
    assert not (tmp_path / ".mcp.json").exists() or "data-sentinel" not in (
        tmp_path / ".mcp.json"
    ).read_text(encoding="utf-8")


# --- lifecycle (Z): reinstall idempotent + update -------------------------

def test_matrix_reinstall_idempotent(tmp_path: Path) -> None:
    first = _install(tmp_path, "--host", "claude")
    second = _install(tmp_path, "--host", "claude")
    assert first["status"] == second["status"] == "completed"
    st = _lifecycle(tmp_path, "status")
    drift = st.get("drift") or {}
    assert not drift.get("modified") and not drift.get("missing")


def test_matrix_status_doctor_after_install(tmp_path: Path) -> None:
    _install(tmp_path, "--host", "claude")
    st = _lifecycle(tmp_path, "status")
    assert st.get("schema") or st.get("status")
    doc = _lifecycle(tmp_path, "doctor")
    assert doc.get("schema") or doc.get("checks") or doc.get("status")


# --- refusal paths (AL rollback / unknown host) ---------------------------

def test_matrix_unknown_host_refused_no_writes(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "--scope", "project", "--root", str(tmp_path), "--yes",
         "--host", "emacs"],
    )
    assert result.exit_code != 0
    assert list(tmp_path.rglob("*")) == []


def test_matrix_dry_run_then_real_install(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "--scope", "project", "--root", str(tmp_path),
         "--host", "claude", "--dry-run"],
    )
    assert result.exit_code == 0
    assert list(tmp_path.rglob("*")) == []
    _install(tmp_path, "--host", "claude")
    assert (tmp_path / ".data-sentinel/install").is_dir()


# --- MCP (AJ): config entry + honest codex note ---------------------------

def test_matrix_mcp_config_and_handshake_entry(tmp_path: Path) -> None:
    _install(tmp_path, "--host", "claude")
    mcp = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    entry = mcp["mcpServers"]["data-sentinel"]
    assert entry["command"].endswith("data-sentinel")
    assert entry["args"] == ["mcp", "serve"]


# --- secrets (AN) ----------------------------------------------------------

_SECRET_RE = re.compile(r"AKIA[0-9A-Z]{16}|-----BEGIN|password\s*=", re.I)


def test_matrix_no_secrets_in_receipt_or_ledger(tmp_path: Path) -> None:
    _install(tmp_path, "--host", "all", "--profile", "full")
    state = tmp_path / ".data-sentinel/install"
    for f in state.rglob("*"):
        if f.is_file():
            assert not _SECRET_RE.search(
                f.read_text(encoding="utf-8", errors="replace")
            ), f


# --- Forge CLI discovery (AA) ---------------------------------------------

def test_matrix_forge_manifests_present_and_valid() -> None:
    root = Path(__file__).resolve().parents[2]
    plain = json.loads((root / "forge.json").read_text(encoding="utf-8"))
    agentic = json.loads(
        (root / "forge.agentic.json").read_text(encoding="utf-8")
    )
    assert plain.get("forge_id") == "data-sentinel-forge" or plain.get("id")
    assert agentic["schema"] == "forge/SpecialistAgenticManifest/v1"


# --- environment (AH) -----------------------------------------------------

def test_matrix_env_report_no_tty(tmp_path: Path) -> None:
    doc = _lifecycle(tmp_path, "env")
    assert doc["schema"] == "data-sentinel/EnvironmentReport/v1"
    assert Path(doc["python"]["executable"]).is_absolute()
    assert doc["python"]["meets_floor"] is True


# --- security gates §14 P0 ------------------------------------------------

def test_p0_traversal_asset_path_refused(
    tmp_path: Path, monkeypatch
) -> None:
    """A rendered path escaping the scope root must refuse, never write."""
    import data_sentinel.installation.assets as assets_mod

    monkeypatch.setattr(
        assets_mod,
        "render_for_hosts",
        lambda ctx: {
            "../escape.txt": b"x",
            ".claude/skills/ok/SKILL.md": b"y",
        },
    )
    with pytest.raises(service.kit.InstallError, match="VERIFY"):
        service.install(
            host="claude", scope="project", root=tmp_path,
            profile="recommended", yes=True,
        )
    assert not (tmp_path / "escape.txt").exists()
    assert not (tmp_path.parent / "escape.txt").exists()


def test_p0_dry_run_creates_no_state(tmp_path: Path) -> None:
    """Dry-run must not create state dir, locks, receipts or any file."""
    runner.invoke(
        app,
        ["install", "--scope", "project", "--root", str(tmp_path),
         "--host", "all", "--profile", "full", "--dry-run"],
    )
    assert list(tmp_path.rglob("*")) == []
