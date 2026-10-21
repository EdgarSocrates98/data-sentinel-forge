"""Deterministic install planner (§2.1-§2.2).

Delegates mechanics to the vendored installkit ``plan()`` (pure — never
writes) and projects the result into the typed :class:`InstallPlan`.
Identical inputs produce an identical ``plan_id`` — no clock, no
dict-order dependence.
"""

from __future__ import annotations

from pathlib import Path

from data_sentinel import _installkit as kit
from data_sentinel.installation import service
from data_sentinel.installation.contracts import (
    ComponentKind,
    GatewayProfile,
    InstallChange,
    InstallPlan,
    InstallProfile,
    InstallScope,
    PlannedAction,
    SourceInfo,
)

_KIND_TO_COMPONENT = {
    "skill": ComponentKind.SKILLS,
    "agent": ComponentKind.AGENTS,
    "mcp": ComponentKind.MCP,
    "config": ComponentKind.HOST_CONFIG,
    "marker": ComponentKind.MARKERS,
    "state": ComponentKind.HOST_CONFIG,
}

_ACTION = {
    "create": PlannedAction.CREATE,
    "update": PlannedAction.UPDATE,
    "unchanged": PlannedAction.SKIP,
    "adopted": PlannedAction.SKIP,
}


def _detect_source(root: Path) -> SourceInfo:
    """How Sentinel itself was obtained (§8.4) — honest detection."""
    import data_sentinel

    pkg = Path(data_sentinel.__file__).resolve()
    method = "installed"
    if (root / "pyproject.toml").is_file() and (root / "src/data_sentinel").is_dir():
        method = "git" if (root / ".git").is_dir() else "dir"
    elif "site-packages" in pkg.as_posix():
        method = "wheel"
    return SourceInfo(method=method, version=data_sentinel.__version__,
                      integrity="asset-manifest")


def plan_installation(
    *,
    scope: InstallScope,
    host: str,
    profile: InstallProfile,
    gateway_profile: GatewayProfile = GatewayProfile.BALANCED,
    root: Path | None = None,
    components: tuple[str, ...] | None = None,
) -> InstallPlan:
    """Build the deterministic plan via the vendored kit engine."""
    refusals: list[str] = []
    try:
        ctx = service._ctx(
            scope.value, root, service._hosts(host), profile.value,
            dry_run=True, components=components,
            gateway_profile=gateway_profile.value,
        )
        doc = kit.plan(ctx)
    except kit.InstallError as exc:
        # Unknown host/scope/profile → refusal, never a guess.
        plan = InstallPlan(
            plan_id="",
            source=_detect_source(root or Path.cwd()),
            scope=scope,
            host=host,
            profile=profile,
            gateway_profile=gateway_profile,
            components=[],
            target_root=str(root or Path.cwd()),
            refusals=[f"{exc.args[0] if exc.args else exc}"],
        )
        plan.plan_id = plan.compute_plan_id()
        return plan

    ledger = kit.Ledger.load(ctx.state_dir)
    changes: list[InstallChange] = []
    conflicts: list[str] = []
    rollback: list[InstallChange] = []

    for f in doc.get("planned_files", []):
        rel = f["path"]
        target = ctx.root / rel
        action = _ACTION.get(f["action"], PlannedAction.CREATE)
        entry = ledger.get(rel)
        if target.exists() and entry is None:
            # Foreign file — kit skips it at apply; surface it at plan time.
            action = PlannedAction.REFUSE
            conflicts.append(f"{rel}: existe e não é gerenciado pelo Sentinel")
            refusals.append(f"{rel}: recusado — arquivo do usuário preservado")
        elif target.exists() and entry is not None:
            action = PlannedAction.BACKUP_UPDATE
        changes.append(
            InstallChange(
                action=action,
                path=str(target),
                component=_KIND_TO_COMPONENT.get(f["kind"], ComponentKind.HOST_CONFIG),
                source_asset=rel,
                sha256=f.get("sha256"),
            )
        )
        rollback.append(
            InstallChange(
                action=PlannedAction.REFUSE,
                path=str(target),
                component=_KIND_TO_COMPONENT.get(f["kind"], ComponentKind.HOST_CONFIG),
                reason="rollback: remover arquivo criado",
            )
        )

    for m in doc.get("planned_markers", []):
        target = ctx.root / m["file"]
        changes.append(
            InstallChange(
                action=PlannedAction.MERGE_JSON
                if m["file"].endswith(".json")
                else PlannedAction.UPDATE,
                path=str(target),
                component=ComponentKind.MARKERS,
                source_asset=m["file"],
                reason=f"marker block {m['marker']}",
            )
        )

    plan = InstallPlan(
        plan_id="",
        source=_detect_source(ctx.root),
        scope=scope,
        host=host,
        profile=profile,
        gateway_profile=gateway_profile,
        components=sorted(
            {c.component for c in changes}, key=lambda c: c.value
        ) or [ComponentKind.MARKERS],
        target_root=str(ctx.root),
        planned_changes=changes,
        conflicts=conflicts,
        refusals=refusals,
        required_permissions=[str(ctx.root)],
        rollback_plan=rollback,
    )
    plan.plan_id = plan.compute_plan_id()
    return plan
