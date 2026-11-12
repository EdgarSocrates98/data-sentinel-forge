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

import dataclasses
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from data_sentinel import __version__
from data_sentinel import _forgecontext as fctx
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
        distribution="data-sentinel-forge",  # M1 — must match pyproject name
        cli_name="data-sentinel",
        python_spec=">=3.11",
        state_dir=STATE_DIR,
        mcp_command=_resolve_mcp_command(),
        mcp_server_name="data-sentinel",
        mcp_verify_tool=None,  # no-arg read-only tool — tools/list is the probe
        version_cmd=("--version",),
        render_assets=_render_assets,
        # Consumer docs (AGENTS.md/CLAUDE.md/AGENT_PROTOCOL.md) sao da
        # camada forge_context — blocos `forge:<forge-id>` + protocolo
        # consolidado, nao markers `data-sentinel-forge:managed`
        # (mesma migracao dos siblings api-forge/spark-aws/platform).
        marker_files=(),
        marker_body="",
        # H1 fix: nested "install" keeps the install state apart from the
        # shared runtime state (~/.data-sentinel/{sentinel.db,session-token})
        # so `uninstall --scope user --purge` can never wipe user data.
        user_state_dir="~/.data-sentinel/install",
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
    if scope == "user":
        # M12 — no host reads ~/AGENTS.md; markers only make sense inside
        # a project/workspace root.
        spec = dataclasses.replace(spec, marker_files=())
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
        # M4 — the .mcp.json merge is a real write; the plan must show it.
        if components is None or "mcp" in components:
            plan["planned_mcp"] = {
                "file": ".mcp.json",
                "server": "data-sentinel",
                "action": "merge-preserve-foreign",
            }
        return plan
    with kit.acquire_lock(state):
        receipt = kit.apply_install(ctx, approved=yes)
        # M3 — receipt + registry writes stay inside the install lock.
        if receipt.get("status") == "completed":
            _register_context(ctx, receipt)
            _drop_stale_doc_entries(ctx)
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
        receipt = kit.repair(ctx)
        # Registry de contexto (recuperacao §9.2): refaz journal encalhado,
        # reclaim de lock velho, rebuild de registry+ROUTING.md — so quando
        # `.forge/context/` ja existe (repair nunca cria residuo num root
        # pristino).
        if (ctx.root / fctx.CONTEXT_DIR).exists():
            try:
                out_ctx = fctx.repair_context(ctx.root)
                receipt["repaired"].extend(f"context:{w}" for w in out_ctx["written"])
                rec = out_ctx.get("recovered")
                receipt.setdefault("checks", []).append(
                    {
                        "id": "context-registry",
                        "status": "PASS",
                        "detail": (
                            f"{out_ctx['status']} ({len(out_ctx['written'])} writes)"
                            + (f"; recovered {rec['op']}:{rec['forge_id']}" if rec else "")
                            + ("; stale lock reclaimed" if out_ctx.get("lock_recovered") else "")
                        ),
                    }
                )
            except fctx.ContextError as exc:
                receipt["skipped"].append(f"context:{exc.kind}")
                receipt.setdefault("checks", []).append(
                    {
                        "id": "context-registry",
                        "status": "BLOCKED",
                        "detail": f"{exc.kind}: {exc.detail}",
                    }
                )
        # Blocos `forge:*` dos consumer docs: re-assert deterministico a
        # partir dos manifests em `.forge/context/` — conteudo do usuario
        # fora dos marcadores nunca e tocado.
        try:
            out_docs = fctx.repair_docs(ctx.root, legacy_tags=_LEGACY_DOC_TAGS)
            receipt["repaired"].extend(f"docs:{w}" for w in out_docs["written"])
            receipt.setdefault("checks", []).append(
                {
                    "id": "consumer-docs",
                    "status": "PASS",
                    "detail": f"{out_docs['status']} ({len(out_docs['written'])} writes)",
                }
            )
        except fctx.ContextError as exc:
            receipt["skipped"].append(f"docs:{exc.kind}")
            receipt.setdefault("checks", []).append(
                {"id": "consumer-docs", "status": "BLOCKED", "detail": f"{exc.kind}: {exc.detail}"}
            )
        return receipt


def uninstall(
    *,
    scope: str = "project",
    root: Path | None = None,
    purge: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    ctx = _ctx(scope, root, (), "recommended", dry_run)
    if dry_run:
        kit.status(ctx)
        return {
            "schema": kit.SCHEMA_RECEIPT,
            "forge_id": FORGE_ID,
            "operation": "uninstall",
            "scope": scope,
            "dry_run": True,
            # M8 — enumerate what uninstall would actually delete.
            "would_remove": kit.Ledger.load(ctx.state_dir).owned_paths(),
            "status": "planned",
            "verification": {"status": "UNVERIFIED"},
            "created_at": kit._utc_now(),
        }
    with kit.acquire_lock(ctx.state_dir):
        doc = kit.uninstall(ctx, purge_state=purge)
        # So chama a camada de contexto quando ha residuo — a transacao
        # adquire lock proprio e criaria `.forge/context/` num root pristino.
        if _docs_leftovers(ctx.root):
            checks = _unregister_context(ctx.root)
            doc.setdefault("checks", []).extend(checks)
            if any(c.get("status") == "BLOCKED" for c in checks):
                doc["status"] = "failed"
        kit.deregister_installation(FORGE_ID)  # M3 — registry must not lie
    return doc


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
        h: [
            *(f"dir:{d}" for d in _HOST_HINTS[h] if (target / d).exists()),
            *(f"bin:{b}" for b in _HOST_BINS[h] if shutil.which(b)),
        ]
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
            for name in _env_knobs()
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
def _env_knobs() -> tuple[str, ...]:
    """M6 — every DATA_SENTINEL_* knob the codebase actually reads.

    ``SentinelConfig`` fields are env-overridable via the documented
    ``DATA_SENTINEL_<FIELD>`` convention (``core/configuration``); the
    three out-of-band knobs (DB/MCP_ROOTS/TOKEN) are read directly.
    """
    from data_sentinel.core.configuration.models import SentinelConfig

    config_knobs = (
        f"DATA_SENTINEL_{name.upper()}"
        for name in SentinelConfig.model_fields
        if name != "sources"
    )
    return tuple(
        sorted(
            (*config_knobs, "DATA_SENTINEL_DB",
             "DATA_SENTINEL_MCP_ROOTS", "DATA_SENTINEL_TOKEN")
        )
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
            "distribution": "data-sentinel-forge",  # M1 — pyproject name
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
    # M3 — real root, not a phantom ~/.forge/installs/<id> path.
    doc["install_root"] = str(ctx.root)
    doc.setdefault(
        "mcp",
        {
            "server_name": "data-sentinel",  # M2 — actual .mcp.json key
            "command": ["data-sentinel", "mcp", "serve"],
            "verified": False,
        },
    )
    kit.register_installation(doc)


# --------------------------------------------------------------------------
# forge-context/v1 wiring (install-2.0 — the-forge ADR-0061, mesmo desenho
# dos siblings api-forge/spark-aws/platform-forge). `.forge/context/` e o
# registry de workspace compartilhado entre forges — camada diferente de
# `~/.forge/installations/` (conta) e de `.data-sentinel/install/` (ledger).
# Este forge so registra e desregistra o proprio `forge_id`.
# --------------------------------------------------------------------------

_PKG_DIR = Path(__file__).resolve().parents[1]
_REPO_DIR = _PKG_DIR.parent.parent  # src/data_sentinel -> repo root

# Markers de geracoes anteriores (`data-sentinel-forge:managed` do installkit
# generico); `install_docs`/`uninstall_docs` os removem ao convergir os
# consumer docs para blocos `forge:*`.
_LEGACY_DOC_TAGS: tuple[str, ...] = ("data-sentinel-forge:managed",)
_CONSUMER_DOCS: tuple[str, ...] = ("AGENTS.md", "CLAUDE.md", "AGENT_PROTOCOL.md")

_DS_DOMAINS: tuple[str, ...] = (
    "data-diagnostics",
    "apache-spark",
    "aws-emr",
    "aws-glue",
    "aws-iam",
    "data-quality",
    "cloud-cost",
    "observability",
)

_ASSETS_DIR = _PKG_DIR / "installation" / "assets"


def _mds(base: Path) -> list[str]:
    return sorted(p.stem for p in base.glob("*.md")) if base.is_dir() else []


def _drop_stale_doc_entries(ctx: kit.InstallContext) -> None:
    """Remove entradas antigas de ledger para os consumer docs: os arquivos
    agora sao gerenciados pela camada forge_context (blocos `forge:*`), nao
    por hash de arquivo inteiro — conteudo do usuario fora dos marcadores
    nao e drift."""
    ledger = kit.Ledger.load(ctx.state_dir)
    changed = False
    for name in _CONSUMER_DOCS:
        if ledger.get(name) is not None:
            ledger.drop(name)
            changed = True
    if changed:
        ledger.save()


def _context_manifest(ctx: kit.InstallContext) -> dict[str, Any]:
    """Manifesto forge/context/v1 das fontes reais: `forge.json` (bundled no
    assets manifest ou checkout) + `forge.agentic.json` (checkout) e o
    catalogo de assets que `_render_assets` instala."""
    def _bundled_json(name: str) -> dict[str, Any] | None:
        for cand in (
            _ASSETS_DIR / "manifest" / name,
            _PKG_DIR / name,
            _REPO_DIR / name,
        ):
            data = kit._load_json(cand, None)
            if isinstance(data, dict):
                return data
        return None

    forge_json = _bundled_json("forge.json")
    agentic = _bundled_json("forge.agentic.json")

    skills_root = _ASSETS_DIR / "skills"
    skills = (
        sorted(d.name for d in skills_root.iterdir() if d.is_dir())
        if skills_root.is_dir()
        else []
    )
    agents = _mds(_ASSETS_DIR / "agents")

    # `cursor` e host-parcial do install (marker + .mcp.json, honesto em
    # `forge.agentic.json#host_partial`) mas NAO faz parte do enum fechado
    # do contrato — o manifesto declara so os hosts do enum.
    hosts = sorted(set(ctx.hosts) & set(fctx.HOSTS))

    checks: list[dict[str, Any]] = [
        {
            "id": "skills-bundle",
            "status": "PASS" if skills else "UNVERIFIED",
            "detail": f"{len(skills)} skills",
        },
        {
            "id": "agent-specs",
            "status": "PASS" if agents else "UNVERIFIED",
            "detail": f"{len(agents)} agents",
        },
    ]
    return fctx.build_manifest(
        forge_id=FORGE_ID,
        name="Data Sentinel Forge",
        version=__version__,
        cli="data-sentinel",
        package="data_sentinel",
        distribution="data-sentinel-forge",
        python_spec=">=3.11",
        scope=ctx.scope,
        profile=ctx.profile,
        hosts=hosts,
        forge_json=forge_json,
        agentic=agentic,
        kind="diagnostic-provider",
        domains=_DS_DOMAINS,
        skills=skills,
        agents=agents,
        protocols=(
            {"id": "forge/v1", "version": "1"},
            {"id": "forge/context/v1", "version": "1"},
            {"id": "forge/context-registry/v1", "version": "1"},
        ),
        discovery_commands=(
            {
                "id": "analyze",
                "argv": ["data-sentinel", "analyze", "--file", "{artifact}"],
                "mode": "diagnostic-only",
                "read_only": True,
                "description": "deterministic artifact diagnostic",
            },
            {
                "id": "spark-explain",
                "argv": ["data-sentinel", "spark", "explain", "--file", "{plan}"],
                "mode": "diagnostic-only",
                "read_only": True,
                "description": "Spark physical-plan analysis",
            },
            {
                "id": "capabilities",
                "argv": ["data-sentinel", "capabilities", "--descriptors"],
                "mode": "diagnostic-only",
                "read_only": True,
                "description": "capability discovery",
            },
            {
                "id": "doctor",
                "argv": ["data-sentinel", "doctor"],
                "mode": "diagnostic-only",
                "read_only": True,
                "description": "environment + installation health",
            },
        ),
        mcp={
            "server_name": "data-sentinel",
            "command": ["data-sentinel", "mcp", "serve"],
        },
        resources={
            "skills-bundle": {
                "kind": "bundled",
                "location": "data_sentinel/installation/assets/skills",
                "optional": False,
            },
            "agents-bundle": {
                "kind": "bundled",
                "location": "data_sentinel/installation/assets/agents",
                "optional": False,
            },
            "install-ledger": {
                "kind": "referenced",
                "location": ".data-sentinel/install",
                "optional": True,
            },
        },
        mutating_verbs=(
            "install",
            "uninstall",
            "repair",
            "import doctor-bundle",
            "import correlate",
        ),
        requires_approval=("install", "uninstall"),
        offline_available=True,
        health={
            "status": "healthy" if skills and agents else "degraded",
            "checks": checks,
        },
        components=ctx.options or None,
        recorded_by="data-sentinel",
    )


def _register_context(ctx: kit.InstallContext, receipt: dict[str, Any]) -> None:
    """Grava `.forge/context/` — manifesto + entrada no registry +
    ROUTING.md + consumer docs, numa UNICA transacao (install-2.0 §9.2).
    Falha vira check BLOCKED nomeado no recibo — e o recibo reporta a
    falha (componente mandatorio), nunca install "completed" sem registry.
    ``scope=user`` tem target=``~``: `~/.forge/` e nivel de conta —
    contexto de workspace nao se escreve la (mesma regra dos siblings)."""
    if ctx.scope == "user":
        return
    try:
        manifest = _context_manifest(ctx)
        out = fctx.install_transaction(
            ctx.root, manifest, owner=FORGE_ID, legacy_tags=_LEGACY_DOC_TAGS
        )
        receipt.setdefault("checks", []).append(
            {
                "id": "context-registry",
                "status": "PASS",
                "detail": f".forge/context {out['status']} ({len(out['written'])} writes)",
            }
        )
        docs = out["docs"]
        receipt.setdefault("checks", []).append(
            {
                "id": "consumer-docs",
                "status": "PASS",
                "detail": f"{docs['status']}: {len(docs['written'])} written, "
                f"{len(docs['kept'])} kept",
            }
        )
    except fctx.ContextError as exc:
        receipt.setdefault("checks", []).append(
            {"id": "context-registry", "status": "BLOCKED", "detail": f"{exc.kind}: {exc.detail}"}
        )
        receipt["status"] = "failed"


def _unregister_context(root: Path) -> list[dict[str, Any]]:
    """Remove manifesto/entry/blocos `forge:*` deste forge numa UNICA
    transacao (§9.2) — so artifacts proprios; docs compartilhados
    regeneram para os sobreviventes."""
    try:
        out = fctx.uninstall_transaction(
            root, FORGE_ID, owner=FORGE_ID, legacy_tags=_LEGACY_DOC_TAGS
        )
        docs = out["docs"]
        return [
            {
                "id": "context-registry",
                "status": "PASS",
                "detail": f".forge/context {out['status']}",
            },
            {
                "id": "consumer-docs",
                "status": "PASS",
                "detail": f"{docs['status']}: {len(docs['written'])} changed",
            },
        ]
    except fctx.ContextError as exc:
        return [
            {
                "id": "context-registry",
                "status": "BLOCKED",
                "detail": f"{exc.kind}: {exc.detail}",
            }
        ]


def _docs_leftovers(root: Path) -> bool:
    """True quando o alvo ainda carrega residuo forge_context — leitura sem
    lock; so um hit justifica o caminho de escrita (nunca criamos
    `.forge/context/` num root pristino)."""
    if (root / fctx.CONTEXT_DIR).exists():
        return True
    needles = (
        f"forge:{FORGE_ID}:",
        f"{fctx.DOC_TAG_ECOSYSTEM}:",
        fctx.PROTOCOL_SENTINEL,
        *_LEGACY_DOC_TAGS,
    )
    for name in _CONSUMER_DOCS:
        path = root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(n in text for n in needles):
            return True
    return False


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
