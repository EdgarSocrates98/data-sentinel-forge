"""Lineage graph + impact tests (ds-0045)."""

from pathlib import Path

from data_sentinel.core.contracts import DatasetReference
from data_sentinel.lineage import parse_openlineage_events
from data_sentinel.lineage.graph import build_graph, impact

FIX = Path(__file__).parent.parent / "fixtures" / "lineage"


def _graph():
    ing = parse_openlineage_events(
        (FIX / "marquez-real.jsonl").read_text(encoding="utf-8"))
    return build_graph(ing.events)


def test_graph_edges() -> None:
    g = _graph()
    assert "s3://lakehouse-curated/analytics/customer_events" in g.downstream[
        "s3://lakehouse-raw/raw/events"]
    assert "s3://lakehouse-curated/analytics/customer_events" in g.upstream[
        "s3://lakehouse-marts/marts/daily_revenue"]


def test_upstream_downstream_walk() -> None:
    g = _graph()
    imp = impact(g, DatasetReference(
        namespace="s3://lakehouse-raw", name="raw/events"))
    down_names = {d.name for d in imp.downstream}
    assert "analytics/customer_events" in down_names
    assert "marts/daily_revenue" in down_names  # transitivo


def test_upstream_of_sink() -> None:
    g = _graph()
    imp = impact(g, DatasetReference(
        namespace="s3://lakehouse-marts", name="marts/daily_revenue"))
    up = {d.name for d in imp.upstream}
    assert "analytics/customer_events" in up
    assert "raw/events" in up


def test_impact_is_potential_only() -> None:
    g = _graph()
    imp = impact(g, DatasetReference(namespace="a", name="b"))
    assert imp.potential_only is True
    assert any("potencial" in ln for ln in imp.limitations)


def test_isolated_dataset_no_impact() -> None:
    g = _graph()
    imp = impact(g, DatasetReference(namespace="x", name="orphan"))
    assert not imp.upstream and not imp.downstream
    assert imp.confidence == 0.0


def test_empty_graph() -> None:
    g = build_graph([])
    assert g.limitations


def test_jobs_tracked() -> None:
    g = _graph()
    imp = impact(g, DatasetReference(
        namespace="s3://lakehouse-curated",
        name="analytics/customer_events"))
    assert "spark.agg.daily_revenue" in imp.affected_entities
