"""CLI integration tests via typer.testing.CliRunner."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from data_sentinel import __version__
from data_sentinel.cli import app

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "fixtures" / "logs"
SQL = ROOT / "fixtures" / "sql"
runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every test runs against a scratch HOME/store."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(ROOT)
    return tmp_path


class TestBasics:
    def test_version(self) -> None:
        r = runner.invoke(app, ["version"])
        assert r.exit_code == 0 and __version__ in r.stdout

    def test_help_lists_all_commands(self) -> None:
        r = runner.invoke(app, ["--help"])
        assert r.exit_code == 0
        for cmd in ("analyze", "report", "doctor", "capabilities", "config", "version"):
            assert cmd in r.stdout

    def test_help_is_ptbr(self) -> None:
        r = runner.invoke(app, ["analyze", "--help"])
        assert "analisar" in r.stdout.lower() or "arquivo" in r.stdout.lower()


class TestAnalyze:
    def test_analyze_log_json(self) -> None:
        r = runner.invoke(
            app,
            ["analyze", "--file", str(LOGS / "glue_oom.log"), "--json"],
        )
        assert r.exit_code == 0, r.output
        report = json.loads(r.stdout)
        assert report["schema_version"] == "1.0.0"
        assert report["findings"]
        assert "oom" in report["summary"] or report["summary"]

    def test_analyze_log_text(self) -> None:
        r = runner.invoke(app, ["analyze", "--file", str(LOGS / "access_denied.log")])
        assert r.exit_code == 0
        assert "relatório" in r.stdout
        assert "evidência" in r.stdout

    def test_analyze_sql_json(self) -> None:
        r = runner.invoke(
            app,
            ["analyze", "--sql", str(SQL / "join_no_predicate.sql"), "--json"],
        )
        assert r.exit_code == 0, r.output
        report = json.loads(r.stdout)
        assert report["findings"]

    def test_analyze_requires_one_input(self) -> None:
        r = runner.invoke(app, ["analyze"])
        assert r.exit_code == 2

    def test_analyze_missing_file_exit_1(self) -> None:
        r = runner.invoke(app, ["analyze", "--file", "nope.log"])
        assert r.exit_code == 1
        assert "erro" in r.stderr.lower() or "erro" in r.output.lower()

    def test_analyze_traversal_rejected(self) -> None:
        r = runner.invoke(app, ["analyze", "--file", "../../etc/hostname"])
        assert r.exit_code == 1
        assert "erro" in r.stderr.lower() or "raízes" in r.output + r.stderr

    def test_analyze_oversized_rejected(self, tmp_path: Path) -> None:
        big = tmp_path / "big.log"
        big.write_bytes(b"x" * 200)
        (tmp_path / "data-sentinel.toml").write_text("max_file_bytes = 100", encoding="utf-8")
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        try:
            r = runner.invoke(app, ["analyze", "--file", "big.log"])
        finally:
            monkeypatch.undo()
        assert r.exit_code == 1

    def test_analyze_malformed_sql_exit_0_unknown(self) -> None:
        r = runner.invoke(app, ["analyze", "--sql", str(SQL / "broken.sql")])
        assert r.exit_code == 0  # parse failure is a limitation, not a crash
        assert "UNKNOWN" in r.stdout or "não pôde ser analisado" in r.stdout

    def test_analyze_no_persist(self, tmp_path: Path) -> None:
        r = runner.invoke(
            app,
            [
                "analyze",
                "--file",
                str(LOGS / "glue_oom.log"),
                "--json",
                "--no-persist",
                "--profile",
                "offline",
            ],
        )
        assert r.exit_code == 0
        store = tmp_path / ".local/share/data-sentinel/sentinel.db"
        assert not store.exists()

    def test_analyze_persists_report(self, tmp_path: Path) -> None:
        r = runner.invoke(
            app,
            ["analyze", "--file", str(LOGS / "glue_oom.log"), "--json"],
        )
        assert r.exit_code == 0
        report_id = json.loads(r.stdout)["report_id"]
        r2 = runner.invoke(app, ["report", "--input", report_id, "--json"])
        assert r2.exit_code == 0
        assert json.loads(r2.stdout)["report_id"] == report_id

    def test_analyze_output_file(self, tmp_path: Path) -> None:
        out = tmp_path / "out.json"
        r = runner.invoke(
            app,
            [
                "analyze",
                "--file",
                str(LOGS / "glue_oom.log"),
                "--output",
                str(out),
                "--no-persist",
            ],
        )
        assert r.exit_code == 0
        assert json.loads(out.read_text(encoding="utf-8"))["schema_version"] == "1.0.0"


class TestReport:
    def test_report_from_file(self, tmp_path: Path) -> None:
        out = tmp_path / "r.json"
        runner.invoke(
            app,
            [
                "analyze",
                "--file",
                str(LOGS / "mixed.log"),
                "--output",
                str(out),
                "--no-persist",
            ],
        )
        r = runner.invoke(app, ["report", "--input", str(out)])
        assert r.exit_code == 0 and "resumo" in r.stdout

    def test_report_missing_id(self) -> None:
        r = runner.invoke(app, ["report", "--input", "nao-existe"])
        assert r.exit_code == 1


class TestDoctorAndCapabilities:
    def test_doctor_runs(self) -> None:
        r = runner.invoke(app, ["doctor"])
        assert r.exit_code in (0, 1)
        assert "PASS" in r.stdout
        assert "analyzer" in r.stdout.lower()

    def test_doctor_json(self) -> None:
        r = runner.invoke(app, ["doctor", "--json"])
        data = json.loads(r.stdout)
        assert "healthy" in data and "checks" in data

    def test_capabilities_lists_analyzers(self) -> None:
        r = runner.invoke(app, ["capabilities", "--json"])
        assert r.exit_code == 0
        ids = [m["capability_id"] for m in json.loads(r.stdout)]
        assert "spark-glue-log-analyzer" in ids
        assert "sql-static-analyzer" in ids


class TestConfigShow:
    def test_config_show_text(self) -> None:
        r = runner.invoke(app, ["config", "show"])
        assert r.exit_code == 0
        assert "profile" in r.stdout and "fontes" in r.stdout

    def test_config_show_json_redacted(self) -> None:
        r = runner.invoke(app, ["config", "show", "--json"])
        data = json.loads(r.stdout)
        assert data["profile"] in ("economy", "balanced", "deep", "offline")

    def test_noninteractive_no_prompts(self) -> None:
        """Every command completes without stdin interaction."""
        r = runner.invoke(
            app,
            ["analyze", "--file", str(LOGS / "glue_oom.log"), "--json"],
            input="",
        )
        assert r.exit_code == 0
