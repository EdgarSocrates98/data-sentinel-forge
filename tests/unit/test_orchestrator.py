"""Tests for ds-0017 — orchestrator, reporting, api/mcp readiness."""

from pathlib import Path

from data_sentinel.analyzers.registry import registry
from data_sentinel.api.contracts import (
    MCP_READINESS_TOOLS,
    ApiDiagnosticRequest,
    ApiError,
    McpToolDescriptor,
)
from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticReport,
    DiagnosticRequest,
    Platform,
    SourceType,
)
from data_sentinel.core.security import InputFile
from data_sentinel.diagnostics.orchestrator import (
    AnalysisLimits,
    run_diagnostics,
)
from data_sentinel.reporting import render_markdown, render_terminal

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures"


def _inp(name: str, text: str | None = None, sub: str = "logs") -> InputFile:
    p = FIXTURES / sub / name
    if text is not None:
        return InputFile(path=p, text=text, size_bytes=len(text.encode()))
    return InputFile(path=p, text=p.read_text(encoding="utf-8"), size_bytes=p.stat().st_size)


def _req(source_type: SourceType) -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=source_type,
        artifact_references=[ArtifactReference(uri="file://x")],
        platform=Platform.SPARK,
    )


class TestOrchestrator:
    def test_pipeline_report(self) -> None:
        out = run_diagnostics(
            _req(SourceType.LOG), [_inp("glue_oom.log")]
        )
        assert out.report is not None
        assert out.report.findings
        assert out.analyzers_run
        assert out.report.analyzer_versions

    def test_analyzer_failure_degrades_to_limitation(self) -> None:
        class Boom:
            analyzer_id = "boom"
            analyzer_version = "0"
            supported_source_types = (SourceType.LOG,)
            supported_platforms = ()
            limitations = ()

            def analyze(self, request, inputs):
                raise RuntimeError("kaboom")

        out = run_diagnostics(
            _req(SourceType.LOG), [_inp("glue_oom.log")], analyzers=[Boom()]
        )
        assert "boom" in out.analyzers_skipped
        assert any("falhou" in lim for lim in out.report.limitations)

    def test_cancellation_skips(self) -> None:
        out = run_diagnostics(
            _req(SourceType.LOG),
            [_inp("glue_oom.log")],
            limits=AnalysisLimits(cancelled=True),
        )
        assert out.analyzers_run == []
        assert out.analyzers_skipped

    def test_recommendations_collected(self) -> None:
        cfg = FIXTURES / "config" / "spark_props.properties"
        from data_sentinel.core.contracts import ExecutionContext

        req = DiagnosticRequest(
            source_type=SourceType.CONFIG,
            artifact_references=[ArtifactReference(uri="file://x")],
            platform=Platform.SPARK,
            execution_context=ExecutionContext(extra={"spark_version": "3.4"}),
        )
        inp = InputFile(
            path=cfg, text=cfg.read_text(encoding="utf-8"),
            size_bytes=cfg.stat().st_size)
        out = run_diagnostics(req, [inp])
        # config advisor puts recs in metadata["recommendations"]
        assert out.recommendations or any(
            r.metadata.get("recommendations") for r in out.results
        )

    def test_duration_ms_present(self) -> None:
        out = run_diagnostics(_req(SourceType.LOG), [_inp("glue_oom.log")])
        assert out.results and all(
            r.duration_ms is not None for r in out.results
        )


class TestReporting:
    def _report(self) -> tuple[DiagnosticReport, list]:
        out = run_diagnostics(_req(SourceType.LOG), [_inp("glue_oom.log")])
        return out.report, out.evidence

    def test_terminal_render(self) -> None:
        report, ev = self._report()
        text = render_terminal(report, ev, mode_label="offline")
        assert "relatório" in text and "modo: offline" in text
        assert "analyzers:" in text

    def test_markdown_render(self) -> None:
        report, ev = self._report()
        md = render_markdown(report, ev, mode_label="offline")
        for section in (
            "## Sumário executivo",
            "## Contexto do job/artefatos",
            "## Achados",
            "## Limitações",
            "## Versões dos analyzers",
        ):
            assert section in md
        assert "**Evidências:**" in md

    def test_markdown_empty_report(self) -> None:
        from datetime import UTC, datetime

        r = DiagnosticReport(
            request_id="x",
            created_at=datetime.now(UTC),
            summary="0 achado(s)",
        )
        md = render_markdown(r, [])
        assert "_Nenhum achado._" in md and "_Nenhuma declarada._" in md


class TestApiMcpReadiness:
    def test_api_request_validation(self) -> None:
        req = ApiDiagnosticRequest(
            source_type=SourceType.LOG,
            platform=Platform.SPARK,
            artifact_references=["file://a.log"],
        )
        assert req.no_persist is True
        # artifact_references required
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ApiDiagnosticRequest(
                source_type=SourceType.LOG, platform=Platform.SPARK, artifact_references=[]
            )

    def test_api_error_shape(self) -> None:
        err = ApiError(code="x", message="m", request_id="r1")
        assert err.details == {}

    def test_mcp_tools_read_only(self) -> None:
        assert MCP_READINESS_TOOLS
        for t in MCP_READINESS_TOOLS:
            assert t.read_only is True
            assert t.name.islower() and "_" in t.name
            assert isinstance(t, McpToolDescriptor)

    def test_fastapi_absent_is_ok(self) -> None:
        # API contracts must be importable without the [api] extra
        import importlib

        mod = importlib.import_module("data_sentinel.api.contracts")
        assert hasattr(mod, "ApiDiagnosticRequest")


class TestRegistryGrowth:
    def test_new_analyzers_registered(self) -> None:
        ids = {a.analyzer_id for a in registry.all()}
        assert {
            "spark-plan-analyzer",
            "join-intelligence-analyzer",
            "spark-config-advisor",
            "cloudwatch-log-analyzer",
        } <= ids
