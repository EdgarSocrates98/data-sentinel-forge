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


def _spec() -> kit.ForgeSpec:
    return kit.ForgeSpec(
        forge_id=FORGE_ID,
        package="data_sentinel",
        distribution="data-sentinel-forge",
        cli_name="data-sentinel",
        python_spec=">=3.11",
        state_dir=STATE_DIR,
        mcp_command=("data-sentinel", "mcp", "serve"),
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

    Filled by ds-0111+ catalogs; returns {} until then.
    """
    from data_sentinel.installation.assets import render_for_hosts

    return render_for_hosts(ctx)


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
        return kit.apply_install(ctx, approved=yes)
    with kit.acquire_lock(state):
        receipt = kit.apply_install(ctx, approved=yes)
    if not dry_run and receipt.get("status") == "completed":
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
