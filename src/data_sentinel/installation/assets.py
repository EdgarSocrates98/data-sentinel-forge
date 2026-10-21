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


def render_for_hosts(ctx: Any) -> dict[str, bytes]:
    """Render host assets for the install context.

    ``ctx.hosts`` selects which host dirs receive mirrors. Empty catalog
    → empty dict (install still records markers/MCP/ledger state).
    """
    source = asset_source()
    if source is None:
        return {}
    out: dict[str, bytes] = {}
    hosts = set(getattr(ctx, "hosts", ()) or ())
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source).as_posix()
        # layout: skills/<name>/..., agents/<name>.md, hosts/<host>/<rel>
        parts = rel.split("/")
        if parts[0] == "hosts":
            if len(parts) < 3 or parts[1] not in hosts:
                continue
            rel = "/".join(parts[2:])
        elif parts[0] in ("skills", "agents"):
            # ds-0111 mirrors these into per-host dirs; for now they are
            # host-agnostic source files — placed by host adapters later.
            continue
        out[rel] = path.read_bytes()
    return dict(sorted(out.items()))
