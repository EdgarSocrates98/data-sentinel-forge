"""Data Sentinel command-line interface."""

import typer

from data_sentinel import __version__

app = typer.Typer(
    name="data-sentinel",
    help="Diagnostica workloads de engenharia de dados com evidência determinística.",
    add_completion=False,
    no_args_is_help=True,
)


@app.callback()
def _main() -> None:
    """Data Sentinel — Intelligent Data Engineering & Agentic Diagnostics Platform."""


@app.command()
def version() -> None:
    """Mostra a versão instalada do data-sentinel."""
    typer.echo(f"data-sentinel {__version__}")
