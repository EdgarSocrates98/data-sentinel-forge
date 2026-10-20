"""E2E scenarios §11 A-E - end-to-end through CLI + orchestrator."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from data_sentinel.cli import app
from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    FindingStatus,
    Platform,
    SourceType,
)
from data_sentinel.core.security import InputFile
from data_sentinel.diagnostics.orchestrator import run_diagnostics

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def _inp(rel: str) -> InputFile:
    p = ROOT / rel
    return InputFile(path=p, text=p.read_text(), size_bytes=p.stat().st_size)


class TestScenarioA:
    """§11-A: SQL local com 4 JOINs → relatório completo."""

    def test_sql_4joins_via_cli(self, tmp_path: Path) -> None:
        out = tmp_path / "report.json"
        r = runner.invoke(
            app,
            [
                "sql", "analyze",
                "--file", str(ROOT / "fixtures" / "joins" / "high_volume_4tables.sql"),
                "--output", str(out), "--no-persist", "--json",
            ],
        )
        assert r.exit_code == 0, r.stdout
        payload = json.loads(r.stdout)
        # 1) findings present; 2) JSON schema fields; 3) report file written
        assert payload["findings"]
        assert payload["schema_version"] == "1.0.0"
        assert payload["analyzer_versions"]
        saved = json.loads(out.read_text())
        assert saved["report_id"] == payload["report_id"]
        # 4) human rendering works on the same report
        r2 = runner.invoke(app, ["report", "show", "--file", str(out)])
        assert r2.exit_code == 0 and "relatório" in r2.stdout


class TestScenarioB:
    """§11-B: plano físico com Exchanges e JOINs → árvore + achados."""

    def test_plan_exchanges_and_joins(self) -> None:
        req = DiagnosticRequest(
            source_type=SourceType.SPARK_PLAN,
            artifact_references=[ArtifactReference(uri="e2e://plan")],
            platform=Platform.SPARK,
        )
        out = run_diagnostics(req, [_inp("fixtures/plans/many_exchanges.txt")])
        plans = out.results[0].metadata["plans"]
        # tree preserved + exchanges counted
        assert plans[0]["operators"]["Exchange"] >= 3
        assert len(plans[0]["shuffle_points"]) >= 3
        # join + shuffle findings exist as investigation candidates
        assert any(
            f.status == FindingStatus.POSSIBLE for f in out.report.findings
        )


class TestScenarioC:
    """§11-C: falha Glue simulada → correlação temporal + exceção primária."""

    def test_glue_failure_correlation(self) -> None:
        req = DiagnosticRequest(
            source_type=SourceType.CLOUDWATCH_LOG,
            artifact_references=[ArtifactReference(uri="e2e://glue")],
            platform=Platform.AWS_GLUE,
        )
        log = (
            "2024-10-20T10:00:01.000Z ERROR TaskSetManager: "
            "java.lang.OutOfMemoryError: Java heap space\n"
            "2024-10-20T10:00:02.000Z WARN Caused by: java.lang.OutOfMemoryError: GC overhead\n"
            "2024-10-20T10:00:05.000Z ERROR TaskSetManager: "
            "ExecutorLostFailure (executor 1 exited)\n"
        )
        inp = InputFile(path=ROOT / "sim.log", text=log, size_bytes=len(log))
        out = run_diagnostics(req, [inp])
        assert out.report.findings
        # correlation metadata present in cloudwatch analyzer result
        cw = next(
            r for r in out.results if r.analyzer_id == "cloudwatch-log-analyzer"
        )
        assert cw.metadata.get("correlation") or cw.metadata.get("incidents") is not None


class TestScenarioD:
    """§11-D: evidência faltante → inconclusivo + o que ajudaria."""

    def test_missing_evidence_inconclusive(self) -> None:
        req = DiagnosticRequest(
            source_type=SourceType.SQL_QUERY,
            artifact_references=[ArtifactReference(uri="e2e://joins")],
            platform=Platform.SPARK,
        )
        # SQL without stats descriptor → join analysis can't claim cardinality
        out = run_diagnostics(
            req, [_inp("fixtures/joins/high_volume_4tables.sql")]
        )
        unknown = [f for f in out.report.findings if f.status == FindingStatus.UNKNOWN]
        assert unknown
        assert any(
            "Faltam" in f.explanation or "insuficiente" in f.explanation
            for f in unknown
        )
        # what would help is spelled out
        assert any(f.validation_steps for f in unknown)
        # no fabricated cardinality
        for a in out.results:
            for x in a.metadata.get("assessments", []):
                if isinstance(x, dict):
                    assert "unavailable" in str(x.get("estimate_basis", "")) or x[
                        "estimate_basis"
                    ] == "unavailable"


class TestScenarioE:
    """§11-E: joins de alto volume (230M/73M/230M/250M) → risco m2m+shuffle."""

    def test_high_volume_risks(self) -> None:
        req = DiagnosticRequest(
            source_type=SourceType.SQL_QUERY,
            artifact_references=[ArtifactReference(uri="e2e://hv")],
            platform=Platform.SPARK,
        )
        out = run_diagnostics(
            req,
            [
                _inp("fixtures/joins/high_volume_4tables.sql"),
                _inp("fixtures/joins/stats_4tables_m2m.json"),
            ],
        )
        # many-to-many risk detected
        assert any(
            "many-to-many" in f.explanation for f in out.report.findings
        )
        # no unsupported real-cardinality claim
        for f in out.report.findings:
            assert "cardinalidade real" not in f.explanation.lower()
        # controlled-experiment recommendations exist
        assert any(
            f.validation_steps or f.recommendations for f in out.report.findings
        )


class TestAwsGated:
    """Real-AWS tests — skipped unless DATA_SENTINEL_AWS_TESTS=1."""

    @pytest.mark.skipif(
        "not os.environ.get('DATA_SENTINEL_AWS_TESTS')",
        reason="env-gated: requires real AWS non-prod credentials",
    )
    def test_glue_get_job_real(self) -> None:
        import os  # noqa: F401

        from data_sentinel.connectors.aws.glue import GlueConnector
        from data_sentinel.connectors.aws.sessions import build_session

        session = build_session()
        connector = GlueConnector(session)
        # read-only sanity: never calls mutating APIs
        jobs = list(connector.get_jobs(limit=1))
        assert isinstance(jobs, list)
