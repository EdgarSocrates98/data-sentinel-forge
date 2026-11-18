"""installkit 1.0.6 behaviors (wave-10 / install-2.1).

- ``resolve_scope``: an explicit ``--root`` is authoritative — an ancestor
  workspace marker can never pull the resolved root ABOVE the explicit path
  (install-2.1 §5.5).
- ``discover_projects``: gitless members count via project manifests
  (``forge.json``/``pyproject.toml``/``package.json``/``forge.agentic.json``),
  symlinks/junctions are never followed, ``IGNORED_DIRS`` and hidden dirs are
  skipped, and a discovered member is never descended into.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from data_sentinel import _installkit as kit
from data_sentinel.installation import service


def _spec():
    return service._spec()


# ---------------------------------------------------------------------------
# resolve_scope — explicit --root wins over ancestor workspace markers
# ---------------------------------------------------------------------------


def test_explicit_root_wins_over_ancestor_workspace_marker(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    member = ws / "member-a"
    member.mkdir(parents=True)
    (ws / "forge.workspace.json").write_text("{}", encoding="utf-8")

    resolved = kit.resolve_scope(_spec(), "workspace", member, explicit=member)
    assert resolved == member


def test_workspace_scope_walks_up_to_marker_without_explicit_root(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    member = ws / "member-a"
    member.mkdir(parents=True)
    (ws / "forge.workspace.json").write_text("{}", encoding="utf-8")

    resolved = kit.resolve_scope(_spec(), "workspace", member, explicit=None)
    assert resolved == ws


def test_workspace_scope_pyproject_marker(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    member = ws / "member-a"
    member.mkdir(parents=True)
    (ws / "pyproject.toml").write_text("[tool.forge.workspace]\n", encoding="utf-8")

    resolved = kit.resolve_scope(_spec(), "workspace", member, explicit=None)
    assert resolved == ws


def test_project_scope_explicit_root_preserved(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "forge.workspace.json").write_text("{}", encoding="utf-8")
    resolved = kit.resolve_scope(_spec(), "project", repo, explicit=repo)
    assert resolved == repo


# ---------------------------------------------------------------------------
# discover_projects — gitless member discovery
# ---------------------------------------------------------------------------


def test_discover_projects_gitless_manifest_markers(tmp_path: Path) -> None:
    (tmp_path / "git-member" / ".git").mkdir(parents=True)
    (tmp_path / "forge-member").mkdir()
    (tmp_path / "forge-member" / "forge.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pyproject-member").mkdir()
    (tmp_path / "pyproject-member" / "pyproject.toml").write_text("[project]\n")
    (tmp_path / "plain-dir").mkdir()

    found = {p.name for p in kit.discover_projects(tmp_path)}
    assert {"git-member", "forge-member", "pyproject-member"} <= found
    assert "plain-dir" not in found


def test_discover_projects_includes_root_when_marked(tmp_path: Path) -> None:
    (tmp_path / "forge.json").write_text("{}", encoding="utf-8")
    found = kit.discover_projects(tmp_path)
    assert tmp_path.resolve() in found


def test_discover_projects_skips_hidden_and_ignored_dirs(tmp_path: Path) -> None:
    node = tmp_path / "node_modules" / "pkg"
    node.mkdir(parents=True)
    (node / "package.json").write_text("{}", encoding="utf-8")
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "forge.json").write_text("{}", encoding="utf-8")
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "forge.json").write_text("{}", encoding="utf-8")

    found = kit.discover_projects(tmp_path)
    names = {p.name for p in found}
    assert "pkg" not in names and ".hidden" not in names and "lib" not in names


def test_discover_projects_never_descends_into_member(tmp_path: Path) -> None:
    outer = tmp_path / "outer"
    inner = outer / "inner"
    inner.mkdir(parents=True)
    (outer / "forge.json").write_text("{}", encoding="utf-8")
    (inner / "forge.json").write_text("{}", encoding="utf-8")

    names = {p.name for p in kit.discover_projects(tmp_path)}
    assert "outer" in names
    assert "inner" not in names  # nested member stays isolated


def test_discover_projects_never_follows_symlinks(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "forge.json").write_text("{}", encoding="utf-8")
    link = tmp_path / "linked"
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable on this platform")
    target_inside = tmp_path / "ws-root"
    target_inside.mkdir()
    inner_link = target_inside / "linked"
    try:
        os.symlink(target, inner_link, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable on this platform")

    names = {p.name for p in kit.discover_projects(target_inside)}
    assert "linked" not in names


def test_discover_projects_respects_max_depth(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b" / "c" / "member"
    deep.mkdir(parents=True)
    (deep / "forge.json").write_text("{}", encoding="utf-8")

    shallow = {p.name for p in kit.discover_projects(tmp_path, max_depth=2)}
    assert "member" not in shallow
    deeper = {p.name for p in kit.discover_projects(tmp_path, max_depth=4)}
    assert "member" in deeper
