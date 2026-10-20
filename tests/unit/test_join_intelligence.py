"""Tests for ds-0014 — join intelligence & cardinality risk."""

import json
from pathlib import Path

import pytest

from data_sentinel.analyzers.spark.joins import JoinIntelligenceAnalyzer
from data_sentinel.analyzers.spark.joins.extractor import (
    extract_from_sql,
    load_stats,
)
from data_sentinel.analyzers.spark.joins.models import JoinForm
from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    FindingStatus,
    Platform,
    SourceType,
)
from data_sentinel.core.security import InputFile

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "joins"


def _load(name: str) -> InputFile:
    p = FIXTURES / name
    return InputFile(path=str(p), text=p.read_text(), size_bytes=p.stat().st_size)


def _request() -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=SourceType.SQL_QUERY,
        artifact_references=[ArtifactReference(uri="file://fixture")],
        platform=Platform.SPARK,
    )


def _analyze(*names: str):
    return JoinIntelligenceAnalyzer().analyze(
        _request(), [_load(n) for n in names]
    )


class TestExtraction:
    def test_join_forms(self) -> None:
        ctx = extract_from_sql(
            "SELECT 1 FROM a "
            "INNER JOIN b ON a.x=b.x "
            "LEFT JOIN c ON a.x=c.x "
            "RIGHT JOIN d ON a.x=d.x "
            "FULL JOIN e ON a.x=e.x "
            "CROSS JOIN f"
        )
        forms = [j.form for j in ctx.joins]
        assert forms == [
            JoinForm.INNER,
            JoinForm.LEFT,
            JoinForm.RIGHT,
            JoinForm.FULL,
            JoinForm.CROSS,
        ]

    def test_semi(self) -> None:
        ctx = extract_from_sql(_load("semi_anti.sql").text)
        assert ctx.joins and ctx.joins[0].form == JoinForm.SEMI

    def test_multi_key(self) -> None:
        ctx = extract_from_sql(
            "SELECT 1 FROM a JOIN b ON a.x=b.x AND a.y=b.y"
        )
        assert len(ctx.joins[0].equality_keys) == 2

    def test_inequality_detected(self) -> None:
        ctx = extract_from_sql(_load("inequality_join.sql").text)
        assert ctx.joins[0].is_inequality

    def test_expression_based_detected(self) -> None:
        ctx = extract_from_sql(_load("expression_join.sql").text)
        assert ctx.joins[0].is_expression_based

    def test_4tables_join_count(self) -> None:
        ctx = extract_from_sql(_load("high_volume_4tables.sql").text)
        assert len(ctx.joins) == 4

    def test_load_stats(self) -> None:
        tables, _runtime, warns = load_stats(
            _load("stats_4tables_unique.json").text
        )
        assert not warns
        assert tables["orders"].row_count == 230_000_000
        assert tables["products"].keys["product_id"].distinct == 2_500_000
        assert _runtime == {}

    def test_load_stats_malformed(self) -> None:
        tables, _runtime, warns = load_stats("{not json")
        assert tables == {} and warns


class TestCardinality:
    def test_unique_stats_m2m_flag(self) -> None:
        result = _analyze("high_volume_4tables.sql", "stats_4tables_unique.json")
        assessments = result.metadata["assessments"]
        _ = [a for a in assessments if a["many_to_many_risk"]]
        # orders⋈customers on customer_id: orders side non-unique (73M distinct
        # in 230M rows), customers unique → N:1, not m2m.
        o2c = next(
            a for a, j in zip(assessments, result.metadata["joins"], strict=False)
            if j["right_table"] == "customers"
        )
        assert o2c["many_to_many_risk"] is False

    def test_m2m_declared_stats(self) -> None:
        result = _analyze("high_volume_4tables.sql", "stats_4tables_m2m.json")
        m2m_findings = [
            f
            for f in result.findings
            if "many-to-many" in f.explanation and f.status == FindingStatus.POSSIBLE
        ]
        assert m2m_findings
        assert "produto das multiplicidades" in m2m_findings[0].explanation
        # deduplication warning present, never auto-suggested
        assert any(
            "NÃO é sugerida automaticamente" in alt
            for f in m2m_findings
            for alt in f.alternatives
        )

    def test_missing_stats_no_cardinality_claim(self) -> None:
        result = _analyze("high_volume_4tables.sql", "stats_missing.json")
        missing = [f for f in result.findings if f.status == FindingStatus.UNKNOWN]
        assert missing
        assert any("Nenhuma cardinalidade é afirmada" in f.explanation for f in missing)
        # never a numeric estimate in metadata without stats
        for a in result.metadata["assessments"]:
            if a["estimate_basis"] == "unavailable":
                assert a["estimated_output"] == "unavailable"

    def test_no_real_cardinality_from_rowcounts(self) -> None:
        result = _analyze("high_volume_4tables.sql", "stats_4tables_unique.json")
        for a in result.metadata["assessments"]:
            if a["estimate_basis"] == "unavailable":
                assert a["estimated_output"] == "unavailable"
            else:
                assert "estimado" in a["estimated_output"]


class TestSkew:
    def test_observed_vs_suspected(self) -> None:
        result = _analyze("high_volume_4tables.sql", "stats_skew.json")
        skews = result.metadata["skew"]
        kinds = {s["kind"] for s in skews}
        assert "observed" in kinds and "suspected" in kinds
        observed_f = [
            f for f in result.findings if "Skew OBSERVADO" in f.explanation
        ]
        assert observed_f and observed_f[0].status == FindingStatus.CONFIRMED
        # stage skew never claims the unbalanced key
        assert "não identifica a chave" in observed_f[0].explanation

    def test_suspected_skew_possible(self) -> None:
        stats = {
            "tables": {
                "orders": {
                    "row_count": 1000,
                    "top_keys": [{"key": "hot", "fraction": 0.4}],
                }
            }
        }
        f = FIXTURES / "_tmp_skew.json"
        f.write_text(json.dumps(stats))
        try:
            result = _analyze("high_volume_4tables.sql", "_tmp_skew.json")
        finally:
            f.unlink()
        suspected = [
            x for x in result.findings if "Skew SUSPEITO" in x.explanation
        ]
        assert suspected and suspected[0].status == FindingStatus.POSSIBLE


class TestGeneral:
    def test_inequality_finding(self) -> None:
        result = _analyze("inequality_join.sql")
        assert any(
            "desigualdade" in f.explanation for f in result.findings
        )

    def test_empty_inputs_unknown(self) -> None:
        empty = InputFile(path="empty.sql", text="SELECT 1", size_bytes=8)
        result = JoinIntelligenceAnalyzer().analyze(_request(), [empty])
        assert any(f.status == FindingStatus.UNKNOWN for f in result.findings)

    def test_metadata_join_listing(self) -> None:
        result = _analyze("high_volume_4tables.sql", "stats_4tables_unique.json")
        assert len(result.metadata["joins"]) == 4
        j = result.metadata["joins"][0]
        assert j["form"] in ("INNER", "LEFT", "RIGHT", "FULL", "CROSS", "SEMI", "ANTI")

    def test_capabilities(self) -> None:
        m = JoinIntelligenceAnalyzer().capabilities()
        assert "analyze_joins" in m.supported_operations


@pytest.mark.parametrize(
    "fixture",
    [
        "high_volume_4tables.sql",
        "inequality_join.sql",
        "expression_join.sql",
        "semi_anti.sql",
    ],
)
def test_sql_fixtures_analyze(fixture: str) -> None:
    result = _analyze(fixture)
    assert result.analyzer_id == "join-intelligence-analyzer"
    assert result.findings
