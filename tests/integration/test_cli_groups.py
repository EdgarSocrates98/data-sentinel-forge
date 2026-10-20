"""Integration tests for ds-0017 CLI groups: spark/sql/report/glue."""

import json
from pathlib import Path

from typer.testing import CliRunner

from data_sentinel.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parent.parent.parent
PLANS = ROOT / "fixtures" / "plans"
SQL = ROOT / "fixtures" / "sql" / "cycle2"


class TestSparkExplain:
    def test_explain_terminal(self) -> None:
        r = runner.invoke(
            app, ["spark", "explain", "--file", str(PLANS / "cartesian.txt"), "--no-persist"]
        )
        assert r.exit_code == 0, r.stdout
        assert "modo: offline" in r.stdout
        assert "CartesianProduct" in r.stdout

    def test_explain_json(self) -> None:
        r = runner.invoke(
            app,
            ["spark", "explain", "--file", str(PLANS / "cartesian.txt"), "--no-persist", "--json"],
        )
        assert r.exit_code == 0
        payload = json.loads(r.stdout)
        assert payload["findings"]

    def test_explain_markdown(self) -> None:
        r = runner.invoke(
            app,
            ["spark", "explain", "--file", str(PLANS / "cartesian.txt"), "--no-persist",
             "--format", "markdown"],
        )
        assert r.exit_code == 0
        assert "## Sumário executivo" in r.stdout

    def test_explain_bad_file(self) -> None:
        r = runner.invoke(
            app, ["spark", "explain", "--file", "/nonexistent/plan.txt"]
        )
        assert r.exit_code == 1


class TestSqlAnalyze:
    def test_sql_analyze(self) -> None:
        r = runner.invoke(
            app,
            ["sql", "analyze", "--file", str(SQL / "cast_keys.sql"), "--no-persist"],
        )
        assert r.exit_code == 0
        assert "CAST em chave" in r.stdout

    def test_sql_dialect(self) -> None:
        r = runner.invoke(
            app,
            ["sql", "analyze", "--file", str(SQL / "athena_query.sql"),
             "--dialect", "trino", "--no-persist", "--json"],
        )
        assert r.exit_code == 0
        assert json.loads(r.stdout)["findings"] is not None


class TestSparkOptimize:
    def test_optimize_composed(self) -> None:
        r = runner.invoke(
            app,
            [
                "spark", "optimize",
                "--sql", str(ROOT / "fixtures" / "joins" / "high_volume_4tables.sql"),
                "--stats", str(ROOT / "fixtures" / "joins" / "stats_4tables_unique.json"),
                "--no-persist",
            ],
        )
        assert r.exit_code == 0, r.stdout
        assert "achado" in r.stdout


class TestReportShow:
    def test_show_from_file(self, tmp_path: Path) -> None:
        out = tmp_path / "r.json"
        runner.invoke(
            app,
            ["spark", "explain", "--file", str(PLANS / "cartesian.txt"),
             "--output", str(out), "--no-persist"],
        )
        r = runner.invoke(app, ["report", "show", "--file", str(out)])
        assert r.exit_code == 0 and "relatório" in r.stdout

    def test_show_markdown(self, tmp_path: Path) -> None:
        out = tmp_path / "r.json"
        runner.invoke(
            app,
            ["spark", "explain", "--file", str(PLANS / "cartesian.txt"),
             "--output", str(out), "--no-persist"],
        )
        r = runner.invoke(app, ["report", "show", "--file", str(out), "--format", "markdown"])
        assert "## Achados" in r.stdout

    def test_legacy_report_input_alias(self, tmp_path: Path) -> None:
        out = tmp_path / "r.json"
        runner.invoke(
            app,
            ["spark", "explain", "--file", str(PLANS / "cartesian.txt"),
             "--output", str(out), "--no-persist"],
        )
        r = runner.invoke(app, ["report", "--input", str(out)])
        assert r.exit_code == 0 and "relatório" in r.stdout


class TestGlueOfflineBehavior:
    def test_diagnose_dry_run(self) -> None:
        r = runner.invoke(
            app, ["glue", "diagnose", "--job", "demo", "--dry-run"]
        )
        assert r.exit_code == 0
        assert "dry-run" in r.stdout
        assert "read-only" in r.stdout

    def test_glue_inspect_needs_aws(self) -> None:
        # without valid AWS creds/profile, must fail cleanly with exit 1
        r = runner.invoke(
            app, ["glue", "inspect", "--job", "x", "--profile", "nonexistent-profile-xyz"]
        )
        assert r.exit_code == 1
        combined = (r.stdout + getattr(r, "stderr", "")).lower()
        assert "boto3" in combined or "perfil" in combined or "aws" in combined
