"""Portable install lifecycle for Data Sentinel — the ``forge/*``
contract v1 implemented over the vendored installkit
(``data_sentinel._installkit``).

Mirrors the sibling-forge pattern (forge-doctor-api
``install/service.py``): the generic engine (ledger, lock, receipts,
marker blocks, managed ``.mcp.json`` key, scope resolution, drift, MCP
handshake) lives in the installkit; this module carries the Sentinel
``ForgeSpec`` and the wrappers the CLI calls.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from data_sentinel import __version__
from data_sentinel import _installkit as kit

FORGE_ID = "data-sentinel-forge"
STATE_DIR = ".data-sentinel/install"
PROFILES: tuple[str, ...] = ("minimal", "recommended", "full")
GATEWAY_PROFILES: tuple[str, ...] = ("economy", "balanced", "deep")
SCOPES: tuple[str, ...] = ("project", "workspace", "user")
# cursor is rendered by asset paths (`.cursor/`) — the kit validates
# nothing by host name; hosts are honest strings we declare.
HOSTS: tuple[str, ...] = ("claude", "devin", "codex", "copilot", "cursor")


MIN_PYTHON = (3, 11)


def _resolve_mcp_command() -> tuple[str, ...]:
    """§7.1 — resolve the server entry point for the host environment.

    Hosts may not inherit the installer's PATH, so the absolute console
    script is preferred; the bare name is the documented fallback.
    """
    resolved = shutil.which("data-sentinel")
    if resolved:
        return (resolved, "mcp", "serve")
    return ("data-sentinel", "mcp", "serve")


def _check_python() -> None:
    """§8.1 — honest refusal below the declared floor."""
    if sys.version_info < MIN_PYTHON:
        v = ".".join(map(str, sys.version_info[:3]))
        need = ".".join(map(str, MIN_PYTHON))
        raise kit.InstallError(
            kit.E_PYTHON,
            f"python {v} < {need} — data-sentinel requires >={need}",
        )


def _detect_source() -> dict[str, Any]:
    """§8.4 — where this installation runs from.

    ``repo`` when a VCS checkout is detected (pyproject.toml sibling of
    ``src/``), ``copied-tree`` for the same layout without ``.git``
    (extracted zip / copied dir), ``installed`` for site-packages
    (wheel/sdist — presence of dist-info ``RECORD`` proves it).
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        pyproject = parent / "pyproject.toml"
        if pyproject.is_file() and (parent / "src" / "data_sentinel").is_dir():
            return {
                "method": "repo" if (parent / ".git").is_dir() else "copied-tree",
                "root": str(parent),
            }
    site = here.parent.parent
    has_dist_info = any(site.glob("data_sentinel*-*.dist-info"))
    return {
        "method": "installed" if has_dist_info else "copied-tree",
        "root": str(site),
    }


def _spec() -> kit.ForgeSpec:
    return kit.ForgeSpec(
        forge_id=FORGE_ID,
        package="data_sentinel",
        distribution="data-sentinel-forge",
        cli_name="data-sentinel",
        python_spec=">=3.11",
        state_dir=STATE_DIR,
        mcp_command=_resolve_mcp_command(),
        mcp_server_name="data-sentinel",
        mcp_verify_tool=None,  # no-arg read-only tool — tools/list is the probe
        version_cmd=("--version",),
        render_assets=_render_assets,
        marker_files=("AGENTS.md", "CLAUDE.md"),
        marker_body=(
            "**Data Sentinel** está instalado neste projeto.\n\n"
            "- MCP server: `data-sentinel` (managed key in `.mcp.json`)\n"
            "- Lifecycle: `data-sentinel install "
            "status|doctor|repair|uninstall`\n\n"
            "Content between the `data-sentinel-forge:managed` markers is "
            "managed; content outside belongs to the user."
        ),
        user_state_dir="~/.data-sentinel",
        spawn_ok=True,  # confined to _spawn(): mcp-verify/update only
    )


def _render_assets(ctx: kit.InstallContext) -> dict[str, bytes]:
    """Host-mirror assets (skills/agents/config) for the chosen hosts.

    P0 gate: every rendered path must be a pure relative path inside the
    scope root — ``..`` segments or absolute paths are refused before the
    installkit ever joins them to ``ctx.root``.
    """
    from data_sentinel.installation.assets import render_for_hosts

    rendered = render_for_hosts(ctx)
    for rel in rendered:
        p = Path(rel)
        if p.is_absolute() or ".." in p.parts:
            raise kit.InstallError(
                kit.E_VERIFY, f"asset path escapes scope root: {rel!r}"
            )
    return rendered


def _ctx(
    scope: str,
    root: Path | None,
    hosts: tuple[str, ...],
    profile: str,
    dry_run: bool,
    components: tuple[str, ...] | None = None,
    gateway_profile: str = "balanced",
) -> kit.InstallContext:
    spec = _spec()
    target = kit.resolve_scope(spec, scope, Path.cwd(), root)
    options = kit.component_options(profile, components)
    options["execution_profile"] = gateway_profile
    return kit.InstallContext(
        spec=spec,
        scope=scope,
        root=target,
        state_dir=kit.state_dir_for(spec, scope, target),
        profile=profile,
        hosts=hosts,
        dry_run=dry_run,
        options=options,
    )


def _hosts(host: str) -> tuple[str, ...]:
    """``all`` → all; ``none``/empty → explicit opt-out; csv → subset."""
    if host == "all":
        return HOSTS
    if not host or host == "none":
        return ()
    names = [h.strip() for h in host.split(",") if h.strip()]
    unknown = [h for h in names if h not in HOSTS]
    if unknown:
        raise kit.InstallError(
            kit.E_HOST, f"host {unknown[0]!r}; known: {list(HOSTS)} + all,none"
        )
    return tuple(dict.fromkeys(names))


def install(
    host: str = "all",
    *,
    scope: str = "project",
    root: Path | None = None,
    profile: str = "recommended",
    yes: bool = False,
    dry_run: bool = False,
    components: tuple[str, ...] | None = None,
    gateway_profile: str = "balanced",
) -> dict[str, Any]:
    """Apply the installation. Without ``yes``/``dry_run`` → refused."""
    _check_python()
    if profile not in PROFILES:
        raise kit.InstallError(kit.E_PROFILE, f"profile {profile!r}; {PROFILES}")
    if gateway_profile not in GATEWAY_PROFILES:
        raise kit.InstallError(
            kit.E_PROFILE, f"gateway_profile {gateway_profile!r}; {GATEWAY_PROFILES}"
        )
    ctx = _ctx(scope, root, _hosts(host), profile, dry_run,
               components=components, gateway_profile=gateway_profile)
    state = ctx.state_dir
    if dry_run:
        # §2.5 — preview must not write, not even the state dir/lock file.
        plan = kit.apply_install(ctx, approved=yes)
        plan["source"] = _detect_source()
        return plan
    with kit.acquire_lock(state):
        receipt = kit.apply_install(ctx, approved=yes)
    if not dry_run and receipt.get("status") == "completed":
        receipt["source"] = _detect_source()
        receipt["source_version"] = __version__
        kit._write_receipt(state, receipt)
        _register(ctx)
    return receipt


def status(*, scope: str = "project", root: Path | None = None) -> dict[str, Any]:
    ctx = _ctx(scope, root, (), "recommended", dry_run=True)
    return kit.status(ctx)


def doctor(*, scope: str = "project", root: Path | None = None) -> dict[str, Any]:
    ctx = _ctx(scope, root, (), "recommended", dry_run=True)
    doc = kit.doctor(ctx)
    if importlib.util.find_spec("mcp") is None:
        doc["checks"] = [
            c
            if c["id"] != "mcp-handshake"
            else {
                **c,
                "status": "UNVERIFIED",
                "detail": "extra 'mcp' not installed — handshake not tested",
            }
            for c in doc["checks"]
        ]
        if not any(c["status"] == "FAIL" for c in doc["checks"]):
            doc["status"] = "healthy" if doc["status"] != "broken" else doc["status"]
    return doc


def repair(
    *, scope: str = "project", root: Path | None = None, dry_run: bool = False
) -> dict[str, Any]:
    ctx = _ctx(scope, root, HOSTS, "full", dry_run)
    if dry_run:
        return kit.status(ctx)
    with kit.acquire_lock(ctx.state_dir):
        return kit.repair(ctx)


def uninstall(
    *,
    scope: str = "project",
    root: Path | None = None,
    purge: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    ctx = _ctx(scope, root, (), "recommended", dry_run)
    if dry_run:
        st = kit.status(ctx)
        return {
            "schema": kit.SCHEMA_RECEIPT,
            "forge_id": FORGE_ID,
            "operation": "uninstall",
            "scope": scope,
            "dry_run": True,
            "would_remove": st.get("drift", {}),
            "status": "planned",
            "verification": {"status": "UNVERIFIED"},
            "created_at": kit._utc_now(),
        }
    with kit.acquire_lock(ctx.state_dir):
        return kit.uninstall(ctx, purge_state=purge)


def environment(
    *, scope: str = "project", root: Path | None = None
) -> dict[str, Any]:
    """§11.1 — environment discovery, read-only and honest.

    Probes the runtime (python/uv/pip/OS/arch), the declared
    ``DATA_SENTINEL_*`` knobs (names only — values are never emitted,
    several are secrets-adjacent), host detection signals at ``root``,
    and existing installs via the forge-neutral ``~/.forge`` registry.
    """
    import platform

    target = kit.resolve_scope(_spec(), scope, Path.cwd(), root)
    host_signals: dict[str, list[str]] = {
        h: list(
            *(f"dir:{d}" for d in _HOST_HINTS[h] if (target / d).exists()),
            *(f"bin:{b}" for b in _HOST_BINS[h] if shutil.which(b)),
        )
        for h in HOSTS
    }
    registry = kit.installations_dir()
    installs = []
    if registry.is_dir():
        for f in sorted(registry.glob("*.json")):
            try:
                doc = json.loads(f.read_text(encoding="utf-8"))
                installs.append({
                    "forge_id": doc.get("forge_id", f.stem),
                    "version": doc.get("version"),
                    "installed_at": doc.get("installed_at"),
                    "scope": doc.get("scope"),
                })
            except (OSError, json.JSONDecodeError):
                installs.append({"forge_id": f.stem, "unreadable": True})
    return {
        "schema": "data-sentinel/EnvironmentReport/v1",
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "meets_floor": sys.version_info >= MIN_PYTHON,
            "floor": ".".join(map(str, MIN_PYTHON)),
        },
        "tools": {
            "uv": bool(shutil.which("uv")),
            "pip": bool(shutil.which("pip")),
            "git": bool(shutil.which("git")),
        },
        "platform": {
            "os": platform.uname().system,
            "arch": platform.uname().machine,
        },
        "scope": {"requested": scope, "resolved_root": str(target)},
        "source": _detect_source(),
        "hosts": host_signals,
        "env_vars": {
            # §11.3 — declared knobs only; values never emitted.
            name: "set" if os.environ.get(name) else "unset"
            for name in sorted(_ENV_KNOBS)
        },
        "forge_registry": {
            "dir": str(registry),
            "installs": installs,
        },
        "notes": [
            "corporate proxies: uv/pip honor HTTPS_PROXY/PIP_INDEX_URL; "
            "data-sentinel itself performs no network I/O",
            "`.env` templates are not shipped — configuration is CLI "
            "flags + DATA_SENTINEL_* env, never overwritten by install",
        ],
    }


# §11.1 — directories each host is known to read (detection hints only;
# these never receive writes by themselves).
_HOST_HINTS: dict[str, tuple[str, ...]] = {
    "claude": (".claude",),
    "devin": (".devin", ".agents"),
    "codex": (".codex", ".agents"),
    "copilot": (".github", ".agents"),
    "cursor": (".cursor",),
}
_HOST_BINS: dict[str, tuple[str, ...]] = {
    "claude": ("claude",),
    "devin": ("devin",),
    "codex": ("codex",),
    "copilot": ("copilot",),
    "cursor": ("cursor",),
}
# Declared DATA_SENTINEL_* knobs read anywhere in the codebase.
_ENV_KNOBS: tuple[str, ...] = (
    "DATA_SENTINEL_DB",
    "DATA_SENTINEL_MCP_ROOTS",
    "DATA_SENTINEL_TOKEN",
)


def mcp_verify() -> dict[str, Any]:
    """Health doc for the MCP handshake check."""
    check = kit.mcp_verify(_spec())
    return {
        "schema": kit.SCHEMA_HEALTH,
        "forge_id": FORGE_ID,
        "status": (
            "healthy"
            if check["status"] == "PASS"
            else "degraded"
            if check["status"] == "FAIL"
            else "unverified"
        ),
        "checks": [check],
        "checked_at": kit._utc_now(),
        "repair_hint": None,
    }


def _receipt(operation: str, checks: list[dict[str, Any]], status: str) -> dict[str, Any]:
    return {
        "schema": kit.SCHEMA_RECEIPT,
        "forge_id": FORGE_ID,
        "operation": operation,
        "managed_files": [],
        "checks": checks,
        "verification": {
            "status": "PASS"
            if all(
                c["status"] in ("PASS", "NOT_APPLICABLE", "UNVERIFIED") for c in checks
            )
            else "FAIL"
        },
        "status": status,
        "created_at": kit._utc_now(),
        "created_by": f"{FORGE_ID}/{__version__}",
    }


def _failed(check_id: str, detail: str, status: str = "failed") -> dict[str, Any]:
    return _receipt("update", [{"id": check_id, "status": "FAIL", "detail": detail}], status)


def _installation_manifest() -> dict[str, Any]:
    path = kit.installations_dir() / f"{FORGE_ID}.json"
    doc = kit._load_json(path, None)
    return doc if isinstance(doc, dict) else {}


def _register(ctx: kit.InstallContext) -> None:
    """Merge ``~/.forge/installations/data-sentinel-forge.json``."""
    existing = _installation_manifest()
    doc: dict[str, Any] = dict(existing)
    doc.update(
        {
            "schema": kit.SCHEMA_MANIFEST,
            "forge_id": FORGE_ID,
            "package": "data_sentinel",
            "distribution": FORGE_ID,
            "cli": {
                "name": "data-sentinel",
                "version_cmd": ["data-sentinel", "--version"],
            },
            "version": __version__,
            "updated_at": kit._utc_now(),
            "installed_at": doc.get("installed_at", kit._utc_now()),
            "installed_by": doc.get(
                "installed_by",
                {"agent": "data-sentinel-cli", "version": __version__},
            ),
            "source": doc.get("source", {"kind": "project-install", "path": str(ctx.root)}),
        }
    )
    doc.setdefault("install_root", str(kit.installs_root() / FORGE_ID))
    doc.setdefault(
        "mcp",
        {
            "server_name": FORGE_ID,
            "command": ["data-sentinel", "mcp", "serve"],
            "verified": False,
        },
    )
    kit.register_installation(doc)


__all__ = [
    "FORGE_ID",
    "GATEWAY_PROFILES",
    "HOSTS",
    "PROFILES",
    "SCOPES",
    "doctor",
    "install",
    "mcp_verify",
    "repair",
    "status",
    "uninstall",
]
