"""Installable asset catalog (skills, agents, host configs, markers).

Source precedence (Grill Gate, hybrid): wheel-packaged
``installation/assets/`` first, repo checkout ``assets/install/``
fallback. ``render_for_hosts`` returns ``{relative_path: bytes}`` — the
installkit writes only these paths, under ledger ownership.

ds-0111+ populates the catalog; until then the base set ships the
Sentinel forge manifest marker only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_PACKAGE_ASSETS = Path(__file__).parent / "assets"


def _repo_root() -> Path | None:
    """Detect a source checkout (pyproject.toml sibling of src/)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src" / "data_sentinel").is_dir():
            return parent
    return None


def _repo_assets() -> Path | None:
    root = _repo_root()
    if root is None:
        return None
    candidate = root / "assets" / "install"
    return candidate if candidate.is_dir() else None


def asset_source() -> Path | None:
    """Packaged assets win; repo fallback second (Grill Gate #1)."""
    if _PACKAGE_ASSETS.is_dir():
        return _PACKAGE_ASSETS
    return _repo_assets()


def load_catalog(source: Path | None = None) -> Any:
    """Read ``assets/`` into an ``AssetCatalog``.

    Layout: ``skills/<name>/<inner>``, ``agents/<stem>.md``,
    ``hosts/<host>/<rel>`` overlays, ``manifest/*`` (kept out of the
    render — ``forge.json`` is Sentinel discovery, not a project asset).
    """
    from data_sentinel.installation.hosts import AssetCatalog

    src = source or asset_source()
    skills: dict[str, dict[str, bytes]] = {}
    agents: dict[str, bytes] = {}
    overlays: dict[str, dict[str, bytes]] = {}
    manifest: dict[str, bytes] = {}
    if src is None or not src.is_dir():
        return AssetCatalog(skills=skills, agents=agents,
                            overlays=overlays, manifest=manifest)
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(src).as_posix()
        parts = rel.split("/")
        if parts[0] == "skills" and len(parts) >= 3:
            skills.setdefault(parts[1], {})["/".join(parts[2:])] = path.read_bytes()
        elif parts[0] == "agents" and len(parts) == 2:
            agents[Path(parts[1]).stem] = path.read_bytes()
        elif parts[0] == "hosts" and len(parts) >= 3:
            overlays.setdefault(parts[1], {})["/".join(parts[2:])] = path.read_bytes()
        elif parts[0] == "manifest" and len(parts) == 2:
            manifest[parts[1]] = path.read_bytes()
    return AssetCatalog(skills=skills, agents=agents,
                        overlays=overlays, manifest=manifest)


def render_for_hosts(ctx: Any) -> dict[str, bytes]:
    """Render host assets for the install context.

    ``ctx.hosts`` selects which host dirs receive mirrors; ``ctx.scope``
    picks project/workspace vs user layouts. Empty catalog → empty dict
    (install still records markers/MCP/ledger state).
    """
    from data_sentinel.installation.hosts import render_hosts

    catalog = load_catalog()
    return render_hosts(
        catalog,
        hosts=tuple(getattr(ctx, "hosts", ()) or ()),
        scope=getattr(ctx, "scope", "project"),
    )
