"""Tests for ds-0015 — SQL analyzer evolution (join graph, dialect, context)."""

from pathlib import Path

from data_sentinel.analyzers.sql.sql_analyzer import SEMANTIC_CHECKLIST, SqlStaticAnalyzer
from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    ExecutionContext,
    Platform,
    SourceType,
)
from data_sentinel.core.security import InputFile

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "sql" / "cycle2"


def _load(name: str) -> InputFile:
    p = FIXTURES / name
    return InputFile(path=str(p), text=p.read_text(), size_bytes=p.stat().st_size)


def _request(platform: Platform = Platform.SPARK) -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=SourceType.SQL_QUERY,
        artifact_references=[ArtifactReference(uri="file://fixture")],
        platform=platform,
    )


def _analyze(*names: str, platform: Platform = Platform.SPARK):
    return SqlStaticAnalyzer().analyze(_request(platform), [_load(n) for n in names])


class TestStructuredMetadata:
    def test_join_graph(self) -> None:
        result = _analyze("multi_join.sql")
        q = result.metadata["queries"][0]
        assert len(q["join_graph"]) == 3
        j = q["join_graph"][0]
        assert j["kind"] == "INNER"
        assert j["predicate"]
        assert j["equality_keys"]

    def test_tables_vs_ctes(self) -> None:
        result = _analyze("cte_heavy.sql")
        q = result.metadata["queries"][0]
        cte_tables = [t for t in q["tables"] if t["is_cte"]]
        real = [t for t in q["tables"] if not t["is_cte"]]
        assert {t["name"] for t in cte_tables} == {"a", "b", "c", "d"}
        assert {"t1", "t2", "t3", "t4"} <= {t["name"] for t in real}
        assert q["cte_count"] == 4

    def test_predicates_aggregations_windows(self) -> None:
        result = _analyze("windowed.sql")
        q = result.metadata["queries"][0]
        assert q["window_functions"] == 1
        result2 = _analyze("multi_join.sql")
        q2 = result2.metadata["queries"][0]
        assert q2["predicates"]

    def test_subquery_depth(self) -> None:
        result = _analyze("deep_subquery.sql")
        assert result.metadata["queries"][0]["subquery_max_depth"] >= 3

    def test_costly_candidates_listed(self) -> None:
        result = _analyze("unfiltered.sql")
        assert "unfiltered-scan" in (
            result.metadata["queries"][0]["costly_operation_candidates"]
        )


class TestNewChecks:
    def test_cast_on_join_key(self) -> None:
        result = _analyze("cast_keys.sql")
        assert any("CAST em chave" in f.explanation for f in result.findings)

    def test_func_on_join_key(self) -> None:
        result = _analyze("func_keys.sql")
        assert any("Função sobre chave" in f.explanation for f in result.findings)

    def test_deep_subquery_flagged(self) -> None:
        result = _analyze("deep_subquery.sql")
        assert any("Subqueries aninhadas" in f.explanation for f in result.findings)

    def test_unfiltered_scan_flagged(self) -> None:
        result = _analyze("unfiltered.sql")
        assert any("sem WHERE/LIMIT" in f.explanation for f in result.findings)

    def test_reused_key_fanout_hint(self) -> None:
        result = _analyze("multi_join.sql")
        assert any(
            "reutilizada" in f.explanation for f in result.findings
        )

    def test_select_star_suppressed_in_exists(self) -> None:
        result = _analyze("legit_exists_star.sql")
        assert not any("projeção ampla" in f.explanation for f in result.findings)

    def test_select_star_suppressed_in_count(self) -> None:
        result = _analyze("legit_count_star.sql")
        assert not any("projeção ampla" in f.explanation for f in result.findings)

    def test_bare_select_star_still_flagged(self) -> None:
        result = _analyze("cte_heavy.sql")
        assert any("projeção ampla" in f.explanation for f in result.findings)


class TestSemanticSafety:
    def test_checklist_on_suggestions(self) -> None:
        result = _analyze("multi_join.sql")
        flagged = [f for f in result.findings if f.recommendations]
        assert flagged
        assert any(
            SEMANTIC_CHECKLIST in r
            for f in flagged
            for r in f.recommendations
        )


class TestDialectEngine:
    def test_engine_spark(self) -> None:
        result = _analyze("multi_join.sql")
        assert result.metadata["engine"] == "spark"
        assert any("Spark" in lim for lim in result.limitations)

    def test_engine_athena(self) -> None:
        result = _analyze("athena_query.sql", platform=Platform.ATHENA)
        assert result.metadata["engine"] == "athena/trino"
        assert result.metadata["dialect"] == "trino"
        assert any("Athena/Trino" in lim for lim in result.limitations)

    def test_explicit_dialect_override(self) -> None:
        req = DiagnosticRequest(
            source_type=SourceType.SQL_QUERY,
            artifact_references=[ArtifactReference(uri="file://x")],
            platform=Platform.GENERIC,
            execution_context=ExecutionContext(extra={"sql_dialect": "trino"}),
        )
        result = SqlStaticAnalyzer().analyze(req, [_load("athena_query.sql")])
        assert result.metadata["dialect"] == "trino"


class TestSelectivity:
    def test_non_selective_with_stats(self) -> None:
        result = _analyze("unfiltered.sql", "stats_selectivity.json")
        assert result.metadata["statistics"]["tables_with_stats"] == ["huge_table"]

    def test_selective_predicate_flag(self) -> None:
        sql = "SELECT id FROM huge_table WHERE status = 'active'"
        f = FIXTURES / "_tmp_sel.sql"
        f.write_text(sql)
        try:
            result = _analyze("_tmp_sel.sql", "stats_selectivity.json")
        finally:
            f.unlink()
        assert any(
            "pouco seletivo" in x.explanation for x in result.findings
        )
