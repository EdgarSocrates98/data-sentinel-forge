"""Bootstrap smoke tests for the installable package."""

from typer.testing import CliRunner

import data_sentinel
from data_sentinel.cli import app


def test_package_exposes_version() -> None:
    assert isinstance(data_sentinel.__version__, str)
    assert data_sentinel.__version__ != ""


def test_cli_help_lists_version_command() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.stdout


def test_cli_version_prints_version() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert data_sentinel.__version__ in result.stdout
