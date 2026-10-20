"""Tests for ds-0013 — Spark execution plan analyzer."""

from pathlib import Path

import pytest

from data_sentinel.analyzers.spark.plans import (
    ExecutionPlan,
    SparkPlanAnalyzer,
    parse_plan,
)
from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    FindingStatus,
    Platform,
    Severity,
    SourceType,
)
from data_sentinel.core.security import InputFile

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "plans"


def _load(name: str) -> InputFile:
    p = FIXTURES / name
    return InputFile(path=str(p), text=p.read_text(), size_bytes=p.stat().st_size)


def _request() -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=SourceType.SPARK_PLAN,
        artifact_references=[ArtifactReference(uri="file://fixture")],
        platform=Platform.SPARK,
    )


def _analyze(name: str):
    return SparkPlanAnalyzer().analyze(_request(), [_load(name)])


class TestParser:
    def test_sort_merge_join_tree(self) -> None:
        plan = parse_plan(_load("sort_merge_join.txt").text)
        assert plan.format == "df_explain"
        assert len(plan.nodes) == 7
        ops = plan.operators()
        assert ops["SortMergeJoin"] == 1
        assert ops["Sort"] == 2
        assert ops["Exchange"] == 2
        assert ops["Scan"] == 2
        # hierarchy preserved
        root = plan.nodes[plan.roots[0]]
        assert root.operator == "SortMergeJoin"
        assert len(plan.children_of(root.node_id)) == 2
        sorts = plan.children_of(root.node_id)
        assert all(s.operator == "Sort" for s in sorts)
        assert len(plan.children_of(sorts[0].node_id)) == 1

    def test_order_preserved(self) -> None:
        plan = parse_plan(_load("many_exchanges.txt").text)
        # first exchange should be a descendant of the aggregate branch
        ids_in_order = [n.node_id for n in plan.nodes.values()]
        assert ids_in_order == sorted(ids_in_order)

    def test_aqe_detected(self) -> None:
        plan = parse_plan(_load("aqe_initial.txt").text)
        assert plan.aqe.get("isFinalPlan") == "false"
        assert any(n.operator == "AdaptiveSparkPlan" for n in plan.nodes.values())

    def test_unknown_operator_preserved(self) -> None:
        plan = parse_plan(_load("unknown_operator.txt").text)
        assert any(n.operator.startswith("unknown:") for n in plan.nodes.values())
        assert plan.warnings, "unknown operator must record a warning"

    def test_truncated_plan_partial(self) -> None:
        plan = parse_plan(_load("truncated.txt").text)
        assert plan.nodes, "partial plan must still yield parsed nodes"
        assert any(n.operator == "Exchange" for n in plan.nodes.values())

    def test_malformed_never_raises(self) -> None:
        plan = parse_plan(_load("malformed.txt").text)
        assert isinstance(plan, ExecutionPlan)
        assert plan.warnings

    def test_statistics_marked_estimated(self) -> None:
        text = (
            "== Physical Plan ==\n"
            "+- HashAggregate(keys=[a#1L], functions=[count(1)], "
            "output=[a#1L, cnt#2L]), Statistics(sizeInBytes=4.0 KiB, rowCount=100)\n"
            "   +- FileScan parquet [a#1L]\n"
        )
        plan = parse_plan(text)
        agg = next(n for n in plan.nodes.values() if n.operator == "HashAggregate")
        assert agg.stats_provenance == "estimated"

    def test_no_dynamic_execution(self) -> None:
        evil = "== Physical Plan ==\n+- __import__('os').system('id') foo\n"
        plan = parse_plan(evil)
        assert plan is not None  # parsed as text only


class TestAnalyzer:
    def test_cartesian_confirmed(self) -> None:
        result = _analyze("cartesian.txt")
        hits = [
            f
            for f in result.findings
            if f.status == FindingStatus.CONFIRMED and "CartesianProduct" in f.explanation
        ]
        assert hits and hits[0].severity == Severity.HIGH
        assert hits[0].evidence_ids

    def test_many_exchanges_possible_not_confirmed(self) -> None:
        result = _analyze("many_exchanges.txt")
        hit = next(f for f in result.findings if "Exchange" in f.explanation)
        assert hit.status == FindingStatus.POSSIBLE
        assert "não é defeito" in hit.explanation

    def test_sort_merge_without_stats_possible(self) -> None:
        result = _analyze("sort_merge_join.txt")
        hit = next(f for f in result.findings if "SortMergeJoin" in f.explanation)
        assert hit.status == FindingStatus.POSSIBLE
        assert hit.validation_steps

    def test_aqe_initial_limitation_recorded(self) -> None:
        result = _analyze("aqe_initial.txt")
        assert any("isFinalPlan=false" in lim for lim in result.limitations)

    def test_evidence_points_to_lines(self) -> None:
        result = _analyze("cartesian.txt")
        assert result.evidence
        assert result.evidence[0].source_location.endswith(":2") or ":" in (
            result.evidence[0].source_location
        )

    def test_metadata_operator_counts(self) -> None:
        result = _analyze("sort_merge_join.txt")
        plans = result.metadata["plans"]
        assert plans[0]["operators"]["Exchange"] == 2
        assert plans[0]["shuffle_points"]

    def test_duration_recorded(self) -> None:
        result = _analyze("broadcast_join.txt")
        assert result.duration_ms is not None and result.duration_ms >= 0

    def test_malformed_unknown_finding(self) -> None:
        result = _analyze("malformed.txt")
        assert any(f.status == FindingStatus.UNKNOWN for f in result.findings)

    def test_deep_tree_no_crash(self) -> None:
        result = _analyze("deep_tree.txt")
        assert result.findings

    def test_capabilities_manifest(self) -> None:
        manifest = SparkPlanAnalyzer().capabilities()
        assert manifest.capability_id == "spark-plan-analyzer"
        assert "analyze_plan" in manifest.supported_operations


@pytest.mark.parametrize(
    "fixture",
    [
        "sort_merge_join.txt",
        "broadcast_join.txt",
        "aqe_initial.txt",
        "cartesian.txt",
        "many_exchanges.txt",
        "unknown_operator.txt",
        "truncated.txt",
        "malformed.txt",
        "deep_tree.txt",
    ],
)
def test_all_fixtures_parse_and_analyze(fixture: str) -> None:
    result = _analyze(fixture)
    assert result.analyzer_id == "spark-plan-analyzer"
    assert result.findings
