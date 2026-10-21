"""``data-sentinel install`` — interactive + non-interactive installer.

The plan is the contract: writes only happen after ``--yes`` (non-TTY)
or interactive confirmation (TTY). ``--dry-run`` never writes anything.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer

from data_sentinel import _installkit as kit
from data_sentinel.installation import service
from data_sentinel.installation.contracts import (
    GatewayProfile,
    InstallProfile,
    InstallScope,
)
from data_sentinel.installation.planner import plan_installation

install_app = typer.Typer(
    help="Instalação e ciclo de vida (skills/agents/MCP em hosts de IA).",
    invoke_without_command=True,
)

_JSON = Annotated[bool, typer.Option("--json", help="Saída em JSON.")]
_SCOPE = Annotated[
    str, typer.Option("--scope", help="project | workspace | user")
]
_ROOT = Annotated[
    Path | None, typer.Option("--root", help="Raiz do alvo (project/workspace).")
]
_HOST = Annotated[
    str, typer.Option("--host", help="claude|devin|codex|copilot|cursor|all|none")
]


def _emit(doc: dict[str, Any], json_mode: bool) -> None:
    if json_mode:
        typer.echo(json.dumps(doc, ensure_ascii=False, indent=2, default=str))
    else:
        _render_receipt(doc)


def _render_receipt(doc: dict[str, Any]) -> None:
    op = doc.get("operation", "install")
    typer.echo(f"{op}: {doc.get('status', '?')}")
    for f in doc.get("planned_files", doc.get("managed_files", [])):
        typer.echo(f"  {f.get('action', '-'):10} {f['path']}")
    for m in doc.get("planned_markers", doc.get("markers", [])):
        typer.echo(f"  marker     {m['file']} [{m['marker']}]")
    for c in doc.get("checks", []):
        typer.echo(f"  [{c.get('status','?')}] {c.get('id','?')} {c.get('detail','')}")
    for w in doc.get("warnings", []):
        typer.echo(f"  aviso: {w}")


def _interactive_flow(
    scope: str | None, host: str | None, profile: str | None,
    gateway: str | None, components: str | None,
) -> tuple[str, str, str, str, str | None]:
    """Prompt only what's needed, with detected defaults (§3.1)."""
    typer.echo("Data Sentinel — instalação")
    if scope is None:
        scope = typer.prompt(
            "Onde instalar? [project]", default="project", show_default=False
        ).strip()
    if host is None:
        typer.echo(f"hosts: {', '.join(service.HOSTS)} | all | none")
        host = typer.prompt("Para quais hosts? [all]", default="all",
                            show_default=False).strip()
    if profile is None:
        typer.echo("perfis: minimal | recommended | full")
        profile = typer.prompt("Perfil? [recommended]", default="recommended",
                               show_default=False).strip()
    if gateway is None:
        typer.echo("gateway: economy | balanced | deep")
        gateway = typer.prompt("Gateway profile? [balanced]", default="balanced",
                               show_default=False).strip()
    if components is None:
        typer.echo("componentes: skills | agents | mcp | host-config | markers |"
                   " portal-launcher (csv, vazio = perfil)")
        components = typer.prompt(
            "Componentes? [perfil]", default="", show_default=False
        ).strip() or None
    return scope, host, profile, gateway, components


@install_app.callback()
def install_cmd(
    ctx: typer.Context,
    scope: _SCOPE = None,  # type: ignore[assignment]
    root: _ROOT = None,
    host: _HOST = None,  # type: ignore[assignment]
    profile: Annotated[
        str | None, typer.Option("--profile", help="minimal|recommended|full")
    ] = None,
    gateway: Annotated[
        str | None, typer.Option("--gateway", help="economy|balanced|deep")
    ] = None,
    components: Annotated[
        str | None, typer.Option("--components", help="csv de componentes")
    ] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Aprova sem perguntar.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview — não escreve nada.")
    ] = False,
    json_mode: _JSON = False,
) -> None:
    """Instala o Sentinel nos hosts/escopo escolhidos (interativo por padrão)."""
    if ctx.invoked_subcommand:
        return
    tty = sys.stdin.isatty()
    if not tty and not yes and not dry_run:
        # CI / non-TTY: never block on a prompt.
        typer.echo(
            "erro: ambiente não-interativo — use --yes ou --dry-run", err=True
        )
        raise typer.Exit(code=2)

    scope_v = scope or "project"
    host_v = host or "all"
    profile_v = profile or "recommended"
    gateway_v = gateway or "balanced"
    comp_v = tuple(c.strip() for c in components.split(",") if c.strip()) if components else None

    if tty and not yes and not dry_run:
        scope_v, host_v, profile_v, gateway_v, comp_raw = _interactive_flow(
            scope, host, profile, gateway, components
        )
        comp_v = tuple(c.strip() for c in comp_raw.split(",") if c.strip()) if comp_raw else None
        # show the plan, ask once to confirm
        try:
            plan = plan_installation(
                scope=InstallScope(scope_v), host=host_v,
                profile=InstallProfile(profile_v),
                gateway_profile=GatewayProfile(gateway_v), root=root,
                components=comp_v,
            )
        except ValueError as exc:
            typer.echo(f"erro: {exc}", err=True)
            raise typer.Exit(code=2) from exc
        typer.echo(f"\nplano {plan.plan_id} — {len(plan.planned_changes)} mudança(s):")
        for c in plan.planned_changes:
            typer.echo(f"  {c.action.value:13} {c.path}")
        for r in plan.refusals:
            typer.echo(f"  recusa: {r}")
        if plan.refusals and not plan.planned_changes:
            typer.echo("nada a aplicar.")
            raise typer.Exit(code=1)
        if not typer.confirm("\nAplicar?", default=False):
            typer.echo("cancelado — nada foi escrito.")
            raise typer.Exit(code=0)
        yes = True

    try:
        doc = service.install(
            host=host_v, scope=scope_v, root=root, profile=profile_v,
            yes=yes, dry_run=dry_run,
            components=comp_v, gateway_profile=gateway_v,
        )
    except kit.InstallError as exc:
        typer.echo(f"erro: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    _emit(doc, json_mode)


def _life(verb: str) -> Callable[..., None]:
    def cmd(
        scope: _SCOPE = "project",
        root: _ROOT = None,
        dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
        json_mode: _JSON = False,
        purge: Annotated[
            bool, typer.Option("--purge", help="Também remove o state dir.")
        ] = False,
    ) -> None:
        try:
            kw: dict[str, Any] = {"scope": scope, "root": root}
            if verb in ("repair", "uninstall"):
                kw["dry_run"] = dry_run
            if verb == "uninstall":
                kw["purge"] = purge
            doc = getattr(service, verb)(**kw)
        except kit.InstallError as exc:
            typer.echo(f"erro: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        _emit(doc, json_mode)
        if doc.get("status") in ("failed", "broken"):
            raise typer.Exit(code=1)

    return cmd


install_app.command("status")(_life("status"))
install_app.command("doctor")(_life("doctor"))
install_app.command("repair")(_life("repair"))
install_app.command("uninstall")(_life("uninstall"))


@install_app.command("mcp-verify")
def mcp_verify_cmd(json_mode: _JSON = False) -> None:
    """Verifica o handshake MCP (initialize + tools/list)."""
    doc = service.mcp_verify()
    _emit(doc, json_mode)
    if doc.get("status") == "degraded":
        raise typer.Exit(code=1)
