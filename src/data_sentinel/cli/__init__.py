"""Data Sentinel command-line interface.

Exit codes (documented in docs/adr): 0 = success, 1 = domain/user error,
2 = usage error (typer), 3 = unexpected internal error.
"""

import json
import sys
from collections.abc import Sequence
from datetime import datetime
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
    InputFile,
    read_input_file,
    safe_resolve,
    sanitize_evidence_excerpt,
)
from data_sentinel.diagnostics.orchestrator import (
    AnalysisLimits,
    run_diagnostics,
)
from data_sentinel.persistence import SentinelStore
from data_sentinel.reporting import render_markdown, render_terminal

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
    report_format: str = "terminal",
    mode_label: str | None = None,
    quiet: bool = False,
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
        outcome = run_diagnostics(
            request, inputs, limits=AnalysisLimits()
        )
        report, evidence = outcome.report, outcome.evidence
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
        if output.suffix in (".md", ".markdown"):
            output.write_text(render_markdown(report, evidence, mode_label=mode_label) + "\n")
        else:
            output.write_text(report.to_json() + "\n")

    if json_mode:
        _emit_json(report.model_dump(mode="json"))
        return
    if quiet:
        typer.echo(report.summary)
        return
    if report_format == "markdown":
        typer.echo(render_markdown(report, evidence, mode_label=mode_label))
    else:
        typer.echo(render_terminal(report, evidence, mode_label=mode_label))


def _print_report(report: DiagnosticReport, evidence: Sequence[Evidence]) -> None:
    typer.echo(render_terminal(report, evidence))


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


# ---------------------------------------------------------------------------
# Cycle 02 — grouped commands (glue / spark / sql / report show)
# ---------------------------------------------------------------------------

glue_app = typer.Typer(help="Inspeção read-only de jobs AWS Glue.")
spark_app = typer.Typer(help="Análise de planos e otimização Spark.")
sql_app = typer.Typer(help="Análise estática de SQL.")
report_app = typer.Typer(
    help="Renderização de relatórios.",
    invoke_without_command=True,
)

app.add_typer(glue_app, name="glue")
app.add_typer(spark_app, name="spark")
app.add_typer(sql_app, name="sql")
app.add_typer(report_app, name="report")

_COMMON_JSON = Annotated[bool, typer.Option("--json", help="Saída em JSON.")]
_QUIET = Annotated[bool, typer.Option("--quiet", "-q", help="Somente resumo.")]
_NO_PERSIST = Annotated[bool, typer.Option("--no-persist", help="Não persiste.")]
_FORMAT = Annotated[
    str, typer.Option("--format", help="terminal|markdown|json")
]


def _aws_glue_connector(profile: str | None, region: str | None) -> Any:
    """Session + connector; fails cleanly without [aws] extra/credentials."""
    from data_sentinel.connectors.aws.glue import GlueConnector
    from data_sentinel.connectors.aws.sessions import build_session

    session = build_session(profile=profile, region=region)
    return GlueConnector(session)


@glue_app.command("inspect")
def glue_inspect(
    job: Annotated[str, typer.Option("--job", help="Nome do job Glue.")],
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    region: Annotated[str | None, typer.Option("--region")] = None,
    json_mode: _COMMON_JSON = False,
    quiet: _QUIET = False,
) -> None:
    """Inspeciona metadados read-only de um job Glue."""
    try:
        connector = _aws_glue_connector(profile, region)
        j = connector.get_job(job)
    except SentinelError as err:
        _fail(err)
        raise AssertionError from err
    payload = {
        "modo": "cloud (aws, read-only)",
        "name": j.name,
        "glue_version": j.glue_version,
        "role": j.role,
        "command": j.command,
        "worker_type": j.worker_type,
        "number_of_workers": j.number_of_workers,
        "default_arguments": j.default_arguments,
    }
    if json_mode:
        _emit_json(payload)
        return
    if quiet:
        typer.echo(f"job {j.name} (glue {j.glue_version})")
        return
    typer.echo("modo: cloud (aws, read-only)")
    for k, v in payload.items():
        if k != "modo":
            typer.echo(f"  {k}: {v}")


@glue_app.command("runs")
def glue_runs(
    job: Annotated[str, typer.Option("--job", help="Nome do job Glue.")],
    limit: Annotated[int, typer.Option("--limit")] = 10,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    region: Annotated[str | None, typer.Option("--region")] = None,
    json_mode: _COMMON_JSON = False,
) -> None:
    """Lista execuções (runs) read-only de um job Glue."""
    try:
        connector = _aws_glue_connector(profile, region)
        runs = connector.get_job_runs(job, limit=limit)
    except SentinelError as err:
        _fail(err)
        raise AssertionError from err
    if json_mode:
        _emit_json(
            {
                "modo": "cloud (aws, read-only)",
                "runs": [r.model_dump(mode="json") for r in runs],
            }
        )
        return
    typer.echo("modo: cloud (aws, read-only)")
    for r in runs:
        typer.echo(
            f"  {r.run_id} | {r.status} | início={r.started_on} "
            f"| duração={r.execution_time}s | erro={r.error_message or '-'}"
        )


@glue_app.command("diagnose")
def glue_diagnose(
    job: Annotated[str, typer.Option("--job", help="Nome do job Glue.")],
    run_id: Annotated[str | None, typer.Option("--run-id")] = None,
    log_group: Annotated[str | None, typer.Option("--log-group")] = None,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    region: Annotated[str | None, typer.Option("--region")] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Mostra o que seria coletado, sem chamar AWS.")
    ] = False,
    no_persist: _NO_PERSIST = False,
    json_mode: _COMMON_JSON = False,
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Coleta metadados + logs de um run Glue e orquestra o diagnóstico."""
    if dry_run:
        typer.echo("modo: dry-run — nenhuma chamada AWS será feita")
        typer.echo(f"  job: {job}")
        typer.echo(f"  run-id: {run_id or '(mais recente)'}")
        typer.echo(f"  log-group: {log_group or '/aws-glue/jobs/output'}")
        typer.echo("  ações: GetJob, GetJobRun(s), GetLogEvents (read-only)")
        return
    try:
        from data_sentinel.connectors.aws.cloudwatch_logs import (
            CloudWatchLogsConnector,
        )
        from data_sentinel.connectors.aws.sessions import build_session

        session = build_session(profile=profile, region=region)
        from data_sentinel.connectors.aws.glue import GlueConnector

        connector = GlueConnector(session)
        run = (
            connector.get_job_run(job, run_id)
            if run_id
            else next(iter(connector.get_job_runs(job, limit=1)))
        )
        group = log_group or run.log_group_name or "/aws-glue/jobs/output"
        logs = CloudWatchLogsConnector(session)
        events = logs.get_log_events(group=group, stream=f"{job}/{run.run_id}")
        text = "\n".join(e.message for e in events) or (
            f"Glue job run {run.run_id} status={run.status} "
            f"error={run.error_message or 'none'}"
        )
        inputs = [
            InputFile(
                path=Path(f"cloudwatch_{job}_{run.run_id}.log"),
                text=text,
                size_bytes=len(text.encode()),
            )
        ]
        request = DiagnosticRequest(
            source_type=SourceType.CLOUDWATCH_LOG,
            artifact_references=[
                ArtifactReference(uri=f"glue://{job}/{run.run_id}")
            ],
            platform=Platform.AWS_GLUE,
        )
        outcome = run_diagnostics(request, inputs)
        report, evidence = outcome.report, outcome.evidence
    except SentinelError as err:
        _fail(err)
        raise AssertionError from err
    except Exception as exc:
        _fail_unexpected(exc)
        raise AssertionError from exc

    if not no_persist:
        try:
            with SentinelStore.from_config(load_config()) as store:
                store.save_analysis(report, request, evidence)
        except SentinelError as err:
            _fail(err)

    if output is not None:
        if output.suffix in (".md", ".markdown"):
            output.write_text(
                render_markdown(report, evidence, mode_label="cloud (aws)") + "\n"
            )
        else:
            output.write_text(report.to_json() + "\n")

    if json_mode:
        _emit_json(report.model_dump(mode="json"))
        return
    typer.echo(render_terminal(report, evidence, mode_label="cloud (aws)"))


@spark_app.command("explain")
def spark_explain(
    file: Annotated[Path, typer.Option("--file", "-f", help="Plano físico (EXPLAIN).")],
    platform: Annotated[Platform, typer.Option("--platform", "-p")] = Platform.SPARK,
    no_persist: _NO_PERSIST = False,
    json_mode: _COMMON_JSON = False,
    quiet: _QUIET = False,
    report_format: _FORMAT = "terminal",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Analisa um plano físico Spark e emite achados de investigação."""
    _analyze(
        source_type=SourceType.SPARK_PLAN,
        paths=[str(file)],
        platform=platform,
        profile=None,
        json_mode=json_mode,
        no_persist=no_persist,
        output=output,
        dialect=None,
        report_format=report_format,
        mode_label="offline",
        quiet=quiet,
    )


@spark_app.command("optimize")
def spark_optimize(
    sql: Annotated[Path, typer.Option("--sql", help="Arquivo SQL a analisar.")],
    dialect: Annotated[
        str, typer.Option("--dialect", help="Dialeto SQL (spark|trino).")
    ] = "spark",
    config: Annotated[
        Path | None, typer.Option("--config", help="Arquivo de configs spark/glue.")
    ] = None,
    stats: Annotated[
        Path | None, typer.Option("--stats", help="Descritor JSON de estatísticas.")
    ] = None,
    no_persist: _NO_PERSIST = False,
    json_mode: _COMMON_JSON = False,
    report_format: _FORMAT = "terminal",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Análise composta: SQL estático + joins/cardinalidade (+config)."""
    paths = [str(sql)] + [str(p) for p in (config, stats) if p]
    _analyze(
        source_type=SourceType.SQL_QUERY,
        paths=paths,
        platform=Platform.SPARK,
        profile=None,
        json_mode=json_mode,
        no_persist=no_persist,
        output=output,
        dialect=dialect,
        report_format=report_format,
        mode_label="offline",
    )


@sql_app.command("analyze")
def sql_analyze(
    file: Annotated[Path, typer.Option("--file", "-f", help="Arquivo SQL.")],
    dialect: Annotated[
        str | None, typer.Option("--dialect", help="spark|trino")
    ] = None,
    platform: Annotated[Platform, typer.Option("--platform", "-p")] = Platform.GENERIC,
    no_persist: _NO_PERSIST = False,
    json_mode: _COMMON_JSON = False,
    quiet: _QUIET = False,
    report_format: _FORMAT = "terminal",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Análise estática de SQL (evolução de `analyze --sql`, mantido)."""
    _analyze(
        source_type=SourceType.SQL_QUERY,
        paths=[str(file)],
        platform=platform,
        profile=None,
        json_mode=json_mode,
        no_persist=no_persist,
        output=output,
        dialect=dialect,
        report_format=report_format,
        mode_label="offline",
        quiet=quiet,
    )


def _render_report_source(
    source: str, report_format: str, json_mode: bool
) -> None:
    """Load report from file path or store id and render it."""
    report_: DiagnosticReport | None = None
    evidence: list[Evidence] = []
    try:
        config = load_config()
        path = Path(source)
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
                report_ = store.get_report(source)
                if report_ is not None:
                    evidence = store.get_evidence(report_.report_id)
        if report_ is None:
            raise SentinelError(
                code="cli.relatorio_nao_encontrado",
                message=f"relatório não encontrado: {source}",
                details={"input": source},
            )
    except SentinelError as err:
        _fail(err)
        raise AssertionError from err
    if json_mode or report_format == "json":
        _emit_json(report_.model_dump(mode="json"))
    elif report_format == "markdown":
        typer.echo(render_markdown(report_, evidence))
    else:
        typer.echo(render_terminal(report_, evidence))


@report_app.callback()
def _report_callback(
    ctx: typer.Context,
    input_: Annotated[
        str | None,
        typer.Option("--input", "-i", help="Alias legado: caminho JSON ou report_id."),
    ] = None,
    report_format: _FORMAT = "terminal",
    json_mode: _COMMON_JSON = False,
) -> None:
    """`data-sentinel report --input X` permanece como alias de `report show`."""
    if ctx.invoked_subcommand is not None:
        return
    if input_ is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=EXIT_OK)
    _render_report_source(input_, report_format, json_mode)


@report_app.command("show")
def report_show(
    file: Annotated[
        Path | None, typer.Option("--file", "-f", help="Arquivo JSON de relatório.")
    ] = None,
    report_id: Annotated[
        str | None, typer.Option("--id", help="ID de relatório persistido.")
    ] = None,
    report_format: _FORMAT = "terminal",
    json_mode: _COMMON_JSON = False,
) -> None:
    """Renderiza relatório persistido ou exportado (terminal/markdown/json)."""
    if (file is None) == (report_id is None):
        typer.echo("erro: informe exatamente uma entrada: --file PATH ou --id ID", err=True)
        raise typer.Exit(code=EXIT_USAGE)
    source = str(file) if file is not None else (report_id or "")
    _render_report_source(source, report_format, json_mode)
