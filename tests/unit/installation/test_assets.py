"""ds-0111+ — catálogo instalável + render por host.

O catálogo canônico mora em ``installation/assets/`` (wheel-first, com
fallback ``assets/install/`` no checkout). ``hosts.py`` mapeia para cada
AI Host os diretórios portados das forjas irmãs; ``render_for_hosts``
devolve ``{caminho relativo: bytes}`` para o installkit escrever.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from typer.main import get_command
from typer.testing import CliRunner

from data_sentinel.cli import app
from data_sentinel.installation import service
from data_sentinel.installation.assets import (
    _PACKAGE_ASSETS,
    asset_source,
    load_catalog,
    render_for_hosts,
)
from data_sentinel.installation.hosts import (
    DISPATCHABLE_SKILLS,
    NON_DISPATCHABLE_SKILLS,
    ORCHESTRATOR_PROFILES,
    SKILL_DISPATCH_REASON,
    UNSUPPORTED_HOSTS,
    AssetCatalog,
    _codex_toml,
    _frontmatter_list,
    frontmatter_scalar,
    layout_for,
    render_hosts,
    split_frontmatter,
)

runner = CliRunner()

ASSETS = _PACKAGE_ASSETS


def _ctx(tmp_path: Path, hosts: tuple[str, ...], profile: str = "full"):
    return service._ctx("project", tmp_path, hosts, profile, True)


# ---------------------------------------------------------------------------
# Integridade do catálogo
# ---------------------------------------------------------------------------


def test_catalog_loads_from_packaged_source() -> None:
    assert asset_source() == _PACKAGE_ASSETS
    catalog = load_catalog()
    assert len(catalog.skills) >= 4
    assert len(catalog.agents) >= 3
    assert "forge.json" in catalog.manifest


def test_skill_dirs_hold_skill_md() -> None:
    catalog = load_catalog()
    for name, files in catalog.skills.items():
        assert "SKILL.md" in files, f"{name}: falta SKILL.md"


def test_every_skill_has_valid_frontmatter() -> None:
    catalog = load_catalog()
    for name, files in sorted(catalog.skills.items()):
        text = files["SKILL.md"].decode("utf-8")
        parsed = split_frontmatter(text)
        assert parsed is not None, f"{name}: sem frontmatter delimitado"
        _, front, _ = parsed
        assert frontmatter_scalar(front, "name") == name
        assert frontmatter_scalar(front, "description")


def test_every_skill_has_dispatch_decision() -> None:
    catalog = load_catalog()
    assert set(catalog.skills) == set(SKILL_DISPATCH_REASON)
    assert not set(DISPATCHABLE_SKILLS) & set(NON_DISPATCHABLE_SKILLS)


def test_agent_manifests_grounded() -> None:
    catalog = load_catalog()
    assert "sentinel-investigator" in ORCHESTRATOR_PROFILES
    for stem, data in sorted(catalog.agents.items()):
        parsed = split_frontmatter(data.decode("utf-8"))
        assert parsed is not None, f"{stem}: sem frontmatter"
        _, front, _ = parsed
        assert frontmatter_scalar(front, "name") == stem
        assert frontmatter_scalar(front, "description")
        assert frontmatter_scalar(front, "tools")


def test_agent_declared_skills_resolve_in_catalog() -> None:
    catalog = load_catalog()
    declared: set[str] = set()
    for data in catalog.agents.values():
        parsed = split_frontmatter(data.decode("utf-8"))
        assert parsed is not None
        declared.update(_frontmatter_list(parsed[1], "skills"))
    assert declared
    assert declared <= set(catalog.skills)


def test_manifest_is_forge_discovery_only() -> None:
    catalog = load_catalog()
    spec = json.loads(catalog.manifest["forge.json"].decode("utf-8"))
    assert spec["forge_id"] == "data-sentinel-forge"
    assert spec["cli"] == "data-sentinel"
    assert spec["mcp_command"] == ["data-sentinel", "mcp", "serve"]


# ---------------------------------------------------------------------------
# Verbos citados existem de verdade
# ---------------------------------------------------------------------------


def _real_verbs() -> tuple[set[str], dict[str, set[str]]]:
    """(comandos de topo, grupo -> subcomandos) da árvore Typer real."""
    root = get_command(app)
    top: set[str] = set()
    groups: dict[str, set[str]] = {}
    for name, sub in root.commands.items():
        top.add(name)
        children = getattr(sub, "commands", None)
        if children:
            groups[name] = set(children)
    return top, groups


_VERB = re.compile(r"data-sentinel\s+([a-z][a-z0-9-]*)(?:\s+([a-z][a-z0-9-]*))?")


def _iter_catalog_text() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    catalog = load_catalog()
    for name, files in catalog.skills.items():
        for inner, data in files.items():
            out.append((f"skills/{name}/{inner}", data.decode("utf-8")))
    for stem, data in catalog.agents.items():
        out.append((f"agents/{stem}.md", data.decode("utf-8")))
    return out


def test_referenced_cli_verbs_exist() -> None:
    top, groups = _real_verbs()
    assert "watch" not in top and "watch" not in groups
    for path, text in _iter_catalog_text():
        for m in _VERB.finditer(text):
            first, second = m.group(1), m.group(2)
            assert first in top, f"{path}: verbo inexistente `data-sentinel {first}`"
            if first in groups and second and not second.startswith("-"):
                assert second in groups[first], (
                    f"{path}: subcomando inexistente "
                    f"`data-sentinel {first} {second}`"
                )


# ---------------------------------------------------------------------------
# Render por host
# ---------------------------------------------------------------------------


def test_render_claude_passthrough(tmp_path: Path) -> None:
    catalog = load_catalog()
    ctx = _ctx(tmp_path, ("claude",))
    out = render_for_hosts(ctx)
    for name, files in catalog.skills.items():
        assert out[f".claude/skills/{name}/SKILL.md"] == files["SKILL.md"]
    for stem, data in catalog.agents.items():
        assert out[f".claude/agents/{stem}.md"] == data


def test_render_devin_native_plus_shared(tmp_path: Path) -> None:
    catalog = load_catalog()
    ctx = _ctx(tmp_path, ("devin",))
    out = render_for_hosts(ctx)
    for name in catalog.skills:
        assert f".devin/skills/{name}/SKILL.md" in out
        assert f".agents/skills/{name}/SKILL.md" in out
    for stem in catalog.agents:
        assert f".devin/agents/{stem}.md" in out
        assert f".agents/agents/{stem}.md" in out
    # frontmatter devin: tools: sai; subagent entra nas despacháveis
    inv = out[".agents/agents/sentinel-investigator.md"].decode("utf-8")
    _, front, _ = split_frontmatter(inv) or ([], [], [])
    assert frontmatter_scalar(front, "tools") is None
    spark = out[".agents/skills/data-sentinel-spark-plan/SKILL.md"].decode("utf-8")
    assert "subagent: true" in spark
    assert "agent: sentinel-spark-specialist" in spark
    investigate = out[
        ".agents/skills/data-sentinel-investigate/SKILL.md"
    ].decode("utf-8")
    assert "subagent" not in investigate.split("---")[1]


def test_render_codex_skills_shared_agents_toml(tmp_path: Path) -> None:
    catalog = load_catalog()
    ctx = _ctx(tmp_path, ("codex",))
    out = render_for_hosts(ctx)
    for name in catalog.skills:
        assert f".agents/skills/{name}/SKILL.md" in out
    assert not any(p.startswith(".agents/agents/") for p in out)
    for stem in catalog.agents:
        toml_path = f".codex/agents/{stem}.toml"
        assert toml_path in out
        assert f".codex/agents/{stem}.md" not in out
        doc = tomllib.loads(out[toml_path].decode("utf-8"))
        assert doc["name"] == stem
        assert doc["description"]
        assert doc["developer_instructions"]


def test_render_copilot_github_layout(tmp_path: Path) -> None:
    catalog = load_catalog()
    ctx = _ctx(tmp_path, ("copilot",))
    out = render_for_hosts(ctx)
    for name in catalog.skills:
        assert f".github/skills/{name}/SKILL.md" in out
    for stem in catalog.agents:
        assert f".github/agents/{stem}.agent.md" in out
        assert out[f".github/agents/{stem}.agent.md"] == catalog.agents[stem]
    assert not any(p.startswith(".agents/") for p in out)


def test_cursor_emits_no_catalog_paths(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, ("cursor",))
    assert render_for_hosts(ctx) == {}
    assert "cursor" in UNSUPPORTED_HOSTS
    assert layout_for("cursor", "project") is None


def test_unknown_host_renders_nothing(tmp_path: Path) -> None:
    catalog = load_catalog()
    assert render_hosts(catalog, hosts=("vim",), scope="project") == {}


def test_manifest_and_forge_json_never_rendered(tmp_path: Path) -> None:
    for host in service.HOSTS:
        out = render_for_hosts(_ctx(tmp_path, (host,)))
        assert not any(
            "manifest" in p or "forge.json" in p for p in out
        ), host


def test_render_is_deterministic_and_sorted(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, service.HOSTS)
    a, b = render_for_hosts(ctx), render_for_hosts(ctx)
    assert a == b
    assert sorted(a) == list(a)


def test_only_selected_hosts_render(tmp_path: Path) -> None:
    out = render_for_hosts(_ctx(tmp_path, ("claude",)))
    assert all(p.startswith(".claude/") for p in out)


def test_overlay_passthrough(tmp_path: Path) -> None:
    import hashlib

    src = tmp_path / "cat"
    (src / "hosts" / "claude").mkdir(parents=True)
    (src / "hosts" / "claude" / "extra.md").write_text("overlay", "utf-8")
    (src / "hosts" / "codex").mkdir(parents=True)
    (src / "hosts" / "codex" / "ignored.md").write_text("no", "utf-8")
    pins = {
        p.relative_to(src).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(src.rglob("*"))
        if p.is_file()
    }
    (src / "MANIFEST.sha256").write_text(json.dumps(pins), "utf-8")
    catalog = load_catalog(src)
    out = render_hosts(catalog, hosts=("claude",), scope="project")
    assert out == {"extra.md": b"overlay"}


def test_codex_toml_escapes_and_requires_fields() -> None:
    import pytest

    toml = _codex_toml("---\nname: x\ndescription: d\n---\ncorpo «q»\n")
    doc = tomllib.loads(toml)
    assert doc["name"] == "x" and "corpo" in doc["developer_instructions"]
    with pytest.raises(ValueError):
        _codex_toml("---\nname: x\n---\nsem description\n")


def test_empty_catalog_renders_nothing(tmp_path: Path) -> None:
    empty = AssetCatalog(skills={}, agents={}, overlays={}, manifest={})
    assert render_hosts(empty, hosts=("claude",), scope="project") == {}


# ---------------------------------------------------------------------------
# Integração install end-to-end
# ---------------------------------------------------------------------------


def test_install_writes_host_assets(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "--root", str(tmp_path), "--host", "claude,codex",
         "--profile", "full", "--yes"],
    )
    assert result.exit_code == 0, result.output
    skill = tmp_path / ".claude/skills/data-sentinel-investigate/SKILL.md"
    assert skill.is_file()
    assert (tmp_path / ".codex/agents/sentinel-investigator.toml").is_file()
    assert not (tmp_path / "forge.json").exists()


def test_minimal_profile_installs_no_skills(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "--root", str(tmp_path), "--host", "claude",
         "--profile", "minimal", "--yes"],
    )
    assert result.exit_code == 0, result.output
    assert not (tmp_path / ".claude").exists()


def test_cursor_install_writes_no_skill_dirs(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "--root", str(tmp_path), "--host", "cursor",
         "--profile", "full", "--yes"],
    )
    assert result.exit_code == 0, result.output
    assert not (tmp_path / ".cursor").exists()
    for d in (".claude", ".devin", ".agents", ".codex", ".github"):
        assert not (tmp_path / d).exists()


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


# ---------------------------------------------------------------------------
# Integrity + source detection (ds-0115 §8)
# ---------------------------------------------------------------------------


def test_asset_manifest_is_current() -> None:
    """MANIFEST.sha256 must cover every catalog file (drift gate)."""
    import hashlib

    src = _PACKAGE_ASSETS
    expected = json.loads((src / "MANIFEST.sha256").read_text())
    actual = {
        p.relative_to(src).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(src.rglob("*"))
        if p.is_file() and p.name != "MANIFEST.sha256"
    }
    assert expected == actual, (
        "catalog changed — regenerate MANIFEST.sha256 via "
        "python scripts or the test helper"
    )


def test_tampered_asset_refuses(tmp_path: Path) -> None:
    import shutil as _sh

    from data_sentinel._installkit import InstallError
    from data_sentinel.installation.assets import verify_integrity

    src = tmp_path / "assets"
    _sh.copytree(_PACKAGE_ASSETS, src)
    target = src / "skills/data-sentinel-sql-review/SKILL.md"
    target.write_text("tampered", encoding="utf-8")
    try:
        verify_integrity(src)
    except InstallError as exc:
        assert exc.kind == "FORGE-INSTALL-VERIFY-FAILED"
    else:
        raise AssertionError("tampered asset was not refused")


def test_missing_manifest_refuses(tmp_path: Path) -> None:
    import shutil as _sh

    from data_sentinel._installkit import InstallError
    from data_sentinel.installation.assets import verify_integrity

    src = tmp_path / "assets"
    _sh.copytree(_PACKAGE_ASSETS, src)
    (src / "MANIFEST.sha256").unlink()
    try:
        verify_integrity(src)
    except InstallError:
        pass
    else:
        raise AssertionError("missing manifest was not refused")


def test_source_detection() -> None:
    source = service._detect_source()
    assert source["method"] in {"repo", "copied-tree", "installed"}
    assert Path(source["root"]).is_dir()


def test_python_floor_check() -> None:
    service._check_python()  # running interpreter is >= 3.11
    import sys as _sys
    real = _sys.version_info
    try:
        _sys.version_info = (3, 9, 0)
        try:
            service._check_python()
        except Exception as exc:
            assert "FORGE-INSTALL-PYTHON-INCOMPATIBLE" in str(exc)
        else:
            raise AssertionError("python < 3.11 was not refused")
    finally:
        _sys.version_info = real


def test_mcp_command_resolution() -> None:
    cmd = service._resolve_mcp_command()
    assert cmd[-2:] == ("mcp", "serve")
    assert cmd[0].endswith("data-sentinel")


def test_mcp_json_preserves_foreign_servers(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text(json.dumps({
        "mcpServers": {"other": {"command": "x", "args": []}},
        "userKey": True,
    }), encoding="utf-8")
    result = runner.invoke(
        app,
        ["install", "--root", str(tmp_path), "--host", "claude",
         "--profile", "minimal", "--yes"],
    )
    assert result.exit_code == 0, result.output
    doc = json.loads((tmp_path / ".mcp.json").read_text())
    assert doc["mcpServers"]["other"]["command"] == "x"
    assert doc["userKey"] is True
    assert "data-sentinel" in doc["mcpServers"]
    assert "_forge_managed" in doc


def test_bootstrap_python_dash_m() -> None:
    import subprocess
    import sys as _sys

    out = subprocess.run(
        [_sys.executable, "-m", "data_sentinel", "--version"],
        capture_output=True, text=True, timeout=30,
    )
    assert out.returncode == 0
    assert "data-sentinel" in out.stdout
