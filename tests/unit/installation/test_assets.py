"""ds-0111/0112/0113 — host adapters + asset catalog tests."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from data_sentinel.cli import app
from data_sentinel.installation import service
from data_sentinel.installation.assets import (
    asset_source,
    load_catalog,
)
from data_sentinel.installation.hosts import (
    DISPATCHABLE_SKILLS,
    NON_DISPATCHABLE_SKILLS,
    UNSUPPORTED_HOSTS,
    frontmatter_scalar,
    layout_for,
    render_hosts,
    split_frontmatter,
)

runner = CliRunner()
ASSETS = Path(__file__).parents[3] / "src/data_sentinel/installation/assets"


# ---------------------------------------------------------------------------
# Catalog integrity (ds-0112/0113)
# ---------------------------------------------------------------------------


def test_catalog_loads_from_package() -> None:
    assert asset_source() == ASSETS
    catalog = load_catalog()
    assert len(catalog.skills) >= 4
    assert len(catalog.agents) >= 3
    assert sorted(catalog.skills) == sorted(DISPATCHABLE_SKILLS | NON_DISPATCHABLE_SKILLS)


def test_every_skill_has_dispatch_decision_and_contract() -> None:
    catalog = load_catalog()
    for name, files in catalog.skills.items():
        md = files["SKILL.md"].decode("utf-8")
        parsed = split_frontmatter(md)
        assert parsed is not None, f"{name}: no frontmatter"
        assert frontmatter_scalar(parsed[1], "name") == name
        assert frontmatter_scalar(parsed[1], "description"), name
        # registered dispatch decision (ds-0111 honest matrix)
        assert name in DISPATCHABLE_SKILLS or name in NON_DISPATCHABLE_SKILLS


def test_agent_manifests_have_name_description_skills() -> None:
    catalog = load_catalog()
    for stem, data in catalog.agents.items():
        parsed = split_frontmatter(data.decode("utf-8"))
        assert parsed is not None, stem
        front = parsed[1]
        assert frontmatter_scalar(front, "name") == stem
        assert frontmatter_scalar(front, "description"), stem


# ---------------------------------------------------------------------------
# Host rendering (ds-0111)
# ---------------------------------------------------------------------------


def test_render_hosts_all_project(tmp_path: Path) -> None:
    catalog = load_catalog()
    out = render_hosts(catalog, hosts=service.HOSTS, scope="project")
    # claude
    assert ".claude/skills/data-sentinel-investigate/SKILL.md" in out
    assert ".claude/agents/sentinel-investigator.md" in out
    # devin double mirror
    assert ".devin/skills/data-sentinel-investigate/SKILL.md" in out
    assert ".devin/agents/sentinel-investigator.md" in out
    # codex TOML agents
    assert ".codex/agents/sentinel-investigator.toml" in out
    assert ".agents/skills/data-sentinel-investigate/SKILL.md" in out
    # copilot .agent.md convention
    assert ".github/agents/sentinel-investigator.agent.md" in out
    assert ".github/skills/data-sentinel-investigate/SKILL.md" in out
    # cursor: honest — nothing rendered
    assert not any(r.startswith(".cursor") for r in out)


def test_unsupported_hosts_documented() -> None:
    assert "cursor" in UNSUPPORTED_HOSTS
    assert layout_for("cursor", "project") is None


def test_devin_mirror_marks_dispatchable_skills() -> None:
    catalog = load_catalog()
    out = render_hosts(catalog, hosts=("devin",), scope="project")
    skill = out[".agents/skills/data-sentinel-spark-plan/SKILL.md"].decode()
    front = split_frontmatter(skill)
    assert front is not None
    assert frontmatter_scalar(front[1], "subagent") == "true"
    # investigator skill is NOT dispatchable — no subagent marker
    inv = out[".agents/skills/data-sentinel-investigate/SKILL.md"].decode()
    assert "subagent: true" not in inv


def test_codex_agent_is_valid_toml() -> None:
    import tomllib

    catalog = load_catalog()
    out = render_hosts(catalog, hosts=("codex",), scope="project")
    for rel, data in out.items():
        if rel.endswith(".toml"):
            parsed = tomllib.loads(data.decode("utf-8"))
            assert parsed["name"] and parsed["description"]
            assert parsed["developer_instructions"]


def test_render_is_deterministic(tmp_path: Path) -> None:
    catalog = load_catalog()
    a = render_hosts(catalog, hosts=service.HOSTS, scope="project")
    b = render_hosts(catalog, hosts=service.HOSTS, scope="project")
    assert a == b and sorted(a) == list(a)


# ---------------------------------------------------------------------------
# Install integration
# ---------------------------------------------------------------------------


def test_install_writes_host_assets(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "--root", str(tmp_path), "--host", "claude,codex",
         "--profile", "full", "--yes"],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude/skills/data-sentinel-investigate/SKILL.md").is_file()
    assert (tmp_path / ".codex/agents/sentinel-investigator.toml").is_file()


def test_minimal_profile_installs_no_skills(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "--root", str(tmp_path), "--host", "claude",
         "--profile", "minimal", "--yes"],
    )
    assert result.exit_code == 0, result.output
    assert not (tmp_path / ".claude").exists()


def test_uninstall_removes_host_assets(tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["install", "--root", str(tmp_path), "--host", "claude",
         "--profile", "full", "--yes"],
    )
    assert (tmp_path / ".claude/skills").is_dir()
    runner.invoke(app, ["install", "uninstall", "--root", str(tmp_path)])
    assert not (tmp_path / ".claude").exists()


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "--root", str(tmp_path), "--host", "claude",
         "--profile", "full", "--dry-run", "--json"],
    )
    assert result.exit_code == 0
    plan = json.loads(result.output)
    planned = {f["path"] for f in plan["planned_files"]}
    assert ".claude/skills/data-sentinel-investigate/SKILL.md" in planned
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / ".data-sentinel").exists()


def test_unknown_host_refuses(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["install", "--root", str(tmp_path), "--host", "vim", "--yes"]
    )
    assert result.exit_code != 0
    assert "vim" in result.output
