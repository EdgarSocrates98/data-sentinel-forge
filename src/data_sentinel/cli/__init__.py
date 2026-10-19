"""Data Sentinel command-line interface.

Exit codes (documented in docs/adr): 0 = success, 1 = domain/user error,
2 = usage error (typer), 3 = unexpected internal error.
"""

import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from data_sentinel import __version__
from data_sentinel.analyzers import AnalysisResult, registry
from data_sentinel.core.configuration import SentinelConfig, load_config
from data_sentinel.core.contracts import (
    AnalysisMode,
    ArtifactReference,
    DiagnosticReport,
    DiagnosticRequest,
    Evidence,
    ExecutionContext,
    Platform,
    SourceType,
)
from data_sentinel.core.exceptions import SentinelError
from data_sentinel.core.security import (
    read_input_file,
    safe_resolve,
    sanitize_evidence_excerpt,
)
from data_sentinel.persistence import SentinelStore

EXIT_OK = 0
EXIT_DOMAIN_ERROR = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

app = typer.Typer(
    name="data-sentinel",
    help="Diagnostica workloads de engenharia de dados com evidência determinística.",
    add_completion=False,
    no_args_is_help=True,
)
config_app = typer.Typer(help="Comandos de configuração.")
app.add_typer(config_app, name="config")

_VERBOSE = False


def _fail(err: SentinelError) -> None:
    typer.echo(f"erro: {err.message} [{err.code}]", err=True)
    if _VERBOSE and err.details:
        typer.echo(json.dumps(err.details, ensure_ascii=False, indent=2), err=True)
    raise typer.Exit(code=EXIT_DOMAIN_ERROR)


def _fail_unexpected(exc: Exception) -> None:
    if _VERBOSE:
        raise exc
    typer.echo(f"erro interno: {exc}", err=True)
    raise typer.Exit(code=EXIT_INTERNAL)


def _emit_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


@app.callback()
def _main(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Mostra detalhes técnicos de erros.")
    ] = False,
) -> None:
    """Data Sentinel — Intelligent Data Engineering & Agentic Diagnostics Platform."""
    global _VERBOSE
    _VERBOSE = verbose


@app.command()
def version() -> None:
    """Mostra a versão instalada do data-sentinel."""
    typer.echo(f"data-sentinel {__version__}")


def _resolve_roots(config: SentinelConfig, cwd: Path) -> list[Path]:
    roots = [cwd.resolve()]
    roots.extend(Path(r).expanduser().resolve() for r in config.allowed_roots)
    return roots


def _build_report(
    request: DiagnosticRequest,
    results: Sequence[AnalysisResult],
    captured: datetime,
) -> tuple[DiagnosticReport, list[Evidence]]:
    findings = [f for r in results for f in r.findings]
    evidence = [e for r in results for e in r.evidence]
    limitations = [lim for r in results for lim in r.limitations]
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.status.value] = counts.get(f.status.value, 0) + 1
    summary = (
        f"{len(findings)} achado(s): "
        + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    )
    report = DiagnosticReport(
        request_id=request.request_id,
        created_at=captured,
        analyzer_versions={r.analyzer_id: r.analyzer_version for r in results},
        findings=findings,
        limitations=limitations,
        summary=summary,
        references=[a.uri for a in request.artifact_references],
    )
    return report, evidence


def _analyze(
    *,
    source_type: SourceType,
    paths: list[str],
    platform: Platform,
    profile: AnalysisMode | None,
    json_mode: bool,
    no_persist: bool,
    output: Path | None,
    dialect: str | None,
) -> None:
    try:
        cli = {"profile": profile.value} if profile else {}
        config = load_config(cli_overrides=cli)
        limits = config.effective_limits()
        roots = _resolve_roots(config, Path.cwd())
        inputs = [
            read_input_file(p, max_file_bytes=limits.max_file_bytes, allowed_roots=roots)
            for p in paths
        ]
        request = DiagnosticRequest(
            source_type=source_type,
            artifact_references=[ArtifactReference(uri=str(i.path)) for i in inputs],
            platform=platform,
            analysis_mode=config.profile,
            execution_context=(
                ExecutionContext(extra={"sql_dialect": dialect}) if dialect else None
            ),
        )
        analyzers = registry.for_source_type(source_type)
        if not analyzers:
            raise SentinelError(
                code="cli.sem_analisador",
                message=f"nenhum analyzer registrado para '{source_type.value}'",
                details={"source_type": source_type.value},
            )
        results = [a.analyze(request, inputs) for a in analyzers]
        report, evidence = _build_report(request, results, datetime.now(UTC))
    except SentinelError as err:
        _fail(err)
        raise AssertionError from err
    except Exception as exc:
        _fail_unexpected(exc)
        raise AssertionError from exc

    if not no_persist:
        try:
            with SentinelStore.from_config(config) as store:
                store.save_analysis(report, request, evidence)
        except SentinelError as err:
            _fail(err)

    if output is not None:
        output.write_text(report.to_json() + "\n")

    if json_mode:
        _emit_json(report.model_dump(mode="json"))
        return
    _print_report(report, evidence)


def _print_report(report: DiagnosticReport, evidence: Sequence[Evidence]) -> None:
    ev_by_id = {e.evidence_id: e for e in evidence}
    typer.echo(f"relatório {report.report_id} (schema {report.schema_version})")
    typer.echo(f"resumo: {report.summary}")
    for finding in report.findings:
        typer.echo(f"\n[{finding.severity.value}/{finding.status.value}] {finding.category.value}")
        typer.echo(f"  {finding.explanation}")
        for ev_id in finding.evidence_ids:
            ev = ev_by_id.get(ev_id)
            if ev:
                typer.echo(f"  evidência: {ev.source_location}")
                typer.echo(f"    {ev.sanitized_excerpt[:200]}")
        for rec in finding.recommendations:
            typer.echo(f"  recomendação: {rec}")
    if report.limitations:
        typer.echo("\nlimitações:")
        for lim in report.limitations:
            typer.echo(f"  - {lim}")


@app.command()
def analyze(
    file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="Arquivo de log a analisar."),
    ] = None,
    sql: Annotated[
        Path | None,
        typer.Option("--sql", help="Arquivo SQL a analisar estaticamente."),
    ] = None,
    platform: Annotated[
        Platform,
        typer.Option("--platform", "-p", help="Plataforma do workload."),
    ] = Platform.GENERIC,
    profile: Annotated[
        AnalysisMode | None,
        typer.Option("--profile", help="Perfil de análise (economy/balanced/deep/offline)."),
    ] = None,
    dialect: Annotated[
        str | None,
        typer.Option("--dialect", help="Sobrescreve o dialeto SQL (ex.: trino)."),
    ] = None,
    json_mode: Annotated[
        bool, typer.Option("--json", help="Saída em JSON para automação.")
    ] = False,
    no_persist: Annotated[
        bool, typer.Option("--no-persist", help="Não persiste o relatório.")
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Grava o relatório JSON neste caminho."),
    ] = None,
) -> None:
    """Analisa um artefato local (log ou SQL) e emite um relatório com evidências."""
    if (file is None) == (sql is None):
        typer.echo(
            "erro: informe exatamente uma entrada: --file PATH ou --sql PATH",
            err=True,
        )
        raise typer.Exit(code=EXIT_USAGE)
    _analyze(
        source_type=SourceType.SQL_QUERY if sql else SourceType.LOG,
        paths=[str(file or sql)],
        platform=platform,
        profile=profile,
        json_mode=json_mode,
        no_persist=no_persist,
        output=output,
        dialect=dialect,
    )


@app.command()
def report(
    input_: Annotated[
        str,
        typer.Option("--input", "-i", help="Caminho do JSON de relatório ou report_id."),
    ],
    json_mode: Annotated[
        bool, typer.Option("--json", help="Ecoa o relatório em JSON.")
    ] = False,
) -> None:
    """Renderiza um relatório persistido ou exportado."""
    report_: DiagnosticReport | None = None
    evidence: list[Evidence] = []
    try:
        config = load_config()
        path = Path(input_)
        if path.is_file():
            resolved = safe_resolve(
                path,
                allowed_roots=[
                    *_resolve_roots(config, Path.cwd()),
                    path.resolve().parent,
                ],
            )
            report_ = DiagnosticReport.from_json(resolved.read_bytes())
        else:
            with SentinelStore.from_config(config) as store:
                report_ = store.get_report(input_)
                if report_ is not None:
                    evidence = store.get_evidence(report_.report_id)
        if report_ is None:
            raise SentinelError(
                code="cli.relatorio_nao_encontrado",
                message=f"relatório não encontrado: {input_}",
                details={"input": input_},
            )
    except SentinelError as err:
        _fail(err)
        raise AssertionError from err
    except Exception as exc:
        _fail_unexpected(exc)
        raise AssertionError from exc
    if json_mode:
        _emit_json(report_.model_dump(mode="json"))
    else:
        _print_report(report_, evidence)


@config_app.command("show")
def config_show(
    json_mode: Annotated[
        bool, typer.Option("--json", help="Saída em JSON (já redigida).")
    ] = False,
) -> None:
    """Mostra a configuração resolvida e as fontes aplicadas."""
    try:
        config = load_config()
    except SentinelError as err:
        _fail(err)
        raise AssertionError from err
    if json_mode:
        _emit_json(config.to_redacted_dict())
        return
    for key, value in config.to_redacted_dict().items():
        if key == "sources":
            continue
        typer.echo(f"{key}: {value}")
    typer.echo("fontes:")
    for source in config.sources:
        mark = "aplicada" if source.applied else ("encontrada" if source.found else "ausente")
        typer.echo(f"  {source.layer}: {source.path or '-'} ({mark})")


@app.command()
def capabilities(
    json_mode: Annotated[
        bool, typer.Option("--json", help="Saída em JSON.")
    ] = False,
) -> None:
    """Lista as capacidades declaradas dos analyzers registrados."""
    manifests = [a.capabilities() for a in registry.all()]
    if json_mode:
        _emit_json([m.model_dump(mode="json") for m in manifests])
        return
    for m in manifests:
        typer.echo(f"{m.capability_id} v{m.version}")
        typer.echo(f"  operações: {', '.join(m.supported_operations) or '-'}")
        typer.echo(f"  plataformas: {', '.join(p.value for p in m.supported_platforms) or '-'}")
        typer.echo(f"  limitações: {len(m.limitations)} declarada(s)")


def _check(label: str, ok: bool, hint: str, warn: bool = False) -> bool:
    mark = "PASS" if ok else ("WARN" if warn else "FAIL")
    typer.echo(f"[{mark}] {label}" + (f" — {hint}" if not ok else ""))
    return ok


@app.command()
def doctor(
    json_mode: Annotated[
        bool, typer.Option("--json", help="Saída em JSON.")
    ] = False,
) -> None:
    """Verifica a saúde da instalação e do ambiente local."""
    results: list[dict[str, Any]] = []

    def rec(label: str, ok: bool, hint: str = "", warn: bool = False) -> bool:
        results.append(
            {
                "check": label,
                "status": "PASS" if ok else ("WARN" if warn else "FAIL"),
                "hint": hint,
            }
        )
        return ok if json_mode else _check(label, ok, hint, warn)

    healthy = True
    py_ok = sys.version_info >= (3, 11)
    healthy &= rec(
        f"python {sys.version.split()[0]}",
        py_ok,
        "requer Python >= 3.11",
    )
    try:
        config = load_config()
        sources = [s for s in config.sources if s.found]
        healthy &= rec(
            f"config resolvida (perfil={config.profile.value}, fontes={len(sources)})", True
        )
    except SentinelError as err:
        config = None
        healthy &= rec("config resolvida", False, err.message)
    if config is not None:
        try:
            with SentinelStore.from_config(config) as store:
                store.list_reports(limit=1)
            healthy &= rec(f"store gravável ({config.store_path})", True)
        except SentinelError as err:
            healthy &= rec("store gravável", False, err.message)
    analyzers = registry.all()
    healthy &= rec(f"{len(analyzers)} analyzer(s) registrado(s)", len(analyzers) >= 1)
    marker = sanitize_evidence_excerpt("password=abc12345")
    healthy &= rec("redação de segredos ativa", "«redacted:" in marker)

    if json_mode:
        _emit_json({"healthy": healthy, "checks": results})
    raise typer.Exit(code=EXIT_OK if healthy else EXIT_DOMAIN_ERROR)
