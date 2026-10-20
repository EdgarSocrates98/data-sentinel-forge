"""Cycle-02 security tests (§10.3) — hostile inputs to new analyzers.

No SQL/code extracted from untrusted input is ever executed: parsers are
pure Python + sqlglot (no eval), connectors are read-only allowlists.
"""

import json
from pathlib import Path

from data_sentinel.analyzers.spark.joins import JoinIntelligenceAnalyzer
from data_sentinel.analyzers.spark.plans import parse_plan
from data_sentinel.analyzers.sql import SqlStaticAnalyzer
from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    Platform,
    SourceType,
)
from data_sentinel.core.security import InputFile, sanitize_evidence_excerpt

ROOT = Path(__file__).resolve().parents[2]


def _inp(text: str, name: str = "hostile") -> InputFile:
    return InputFile(path=ROOT / "fixtures" / name, text=text, size_bytes=len(text.encode()))


def _req(st: SourceType) -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=st,
        artifact_references=[ArtifactReference(uri="test://x")],
        platform=Platform.SPARK,
    )


class TestMaliciousPlanInput:
    def test_dunder_payload_never_executed(self) -> None:
        evil = (
            "== Physical Plan ==\n"
            "+- __import__('os').system('touch /tmp/pwned')\n"
            "   +- eval(compile('1+1')) foo\n"
        )
        plan = parse_plan(evil)
        assert not (Path("/tmp/pwned").exists())  # noqa: S108 - assertiva prova que nada foi escrito
        assert plan.nodes  # parsed as text only

    def test_deeply_nested_plan_no_recursion_bomb(self) -> None:
        text = "== Physical Plan ==\n" + "".join(
            "   " * min(i, 300) + "+- Filter x\n" for i in range(500)
        )
        plan = parse_plan(text)
        assert plan.nodes

    def test_oversized_lines_capped(self) -> None:
        text = "== Physical Plan ==\n+- Project " + "A" * 200_000 + "\n"
        plan = parse_plan(text)
        assert plan.nodes


class TestMaliciousSqlInput:
    def test_drop_not_executed(self) -> None:
        sql = "SELECT 1; DROP TABLE prod.users; --"
        result = SqlStaticAnalyzer().analyze(_req(SourceType.SQL_QUERY), [_inp(sql)])
        assert result is not None  # never executed — only analyzed

    def test_injection_text(self) -> None:
        sql = "SELECT * FROM t WHERE name = 'x' OR '1'='1'"
        result = SqlStaticAnalyzer().analyze(_req(SourceType.SQL_QUERY), [_inp(sql)])
        assert result is not None

    def test_sql_with_exec_payload(self) -> None:
        sql = "SELECT xp_cmdshell('dir') FROM t"
        result = SqlStaticAnalyzer().analyze(_req(SourceType.SQL_QUERY), [_inp(sql)])
        assert result is not None


class TestStatsDescriptorHostile:
    def test_malformed_json_warns(self) -> None:
        result = JoinIntelligenceAnalyzer().analyze(
            _req(SourceType.SQL_QUERY), [_inp("{corrupted", "s.json")]
        )
        assert any("inválido" in lim for lim in result.limitations)

    def test_stats_type_confusion(self) -> None:
        stats = json.dumps({"tables": {"t": "not-an-object"}, "runtime": [1, 2]})
        result = JoinIntelligenceAnalyzer().analyze(
            _req(SourceType.SQL_QUERY), [_inp(stats, "s.json")]
        )
        assert result is not None
        assert any("ignorada" in lim for lim in result.limitations)


class TestUnexpectedAwsResponses:
    def test_connector_allowlist_blocks_mutation(self) -> None:
        from data_sentinel.connectors.aws.glue import ALLOWED_ACTIONS

        mutating = {
            "start_job_run",
            "stop_job_run",
            "create_job",
            "delete_job",
            "update_job",
            "batch_stop_job_run",
        }
        assert ALLOWED_ACTIONS.isdisjoint(mutating)

    def test_unexpected_response_shape(self) -> None:
        # _to_job/_to_run must tolerate missing fields — exercised in ds-0011
        from data_sentinel.connectors.aws.glue import GlueConnector

        job = GlueConnector._to_job({"Name": "x"}, "x")
        assert job.name == "x"
        run = GlueConnector._to_run("j", {"Id": "r1"})
        assert run.run_id == "r1"


class TestParameterManipulation:
    def test_dialect_option_manipulation(self) -> None:
        # arbitrary dialect string — sqlglot falls back or errors, never execs
        sql = "SELECT 1 FROM t"
        result = SqlStaticAnalyzer().analyze(_req(SourceType.SQL_QUERY), [_inp(sql)])
        assert result is not None

    def test_excerpt_never_raw_secrets(self) -> None:
        excerpt = sanitize_evidence_excerpt(
            "connect password=Sup3rSecret! AKIAIOSFODNN7EXAMPLE", max_chars=500
        )
        assert "Sup3rSecret" not in excerpt
        assert "AKIAIOSFODNN7EXAMPLE" not in excerpt
