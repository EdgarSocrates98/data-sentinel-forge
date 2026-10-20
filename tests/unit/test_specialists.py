"""Specialist agents tests (ds-0057)."""

from data_sentinel.agents.specialists import (
    get_specialist,
    plan_tasks,
    route,
    specialist_descriptors,
)


def test_twelve_specialists_with_descriptors() -> None:
    ds = specialist_descriptors()
    assert len(ds) == 12
    ids = {d.agent_id for d in ds}
    assert "coordinator" in ids and "root-cause-analyst" in ids
    for d in ds:
        assert d.policy == "deterministic_first"


def test_allowed_tools_match_registry() -> None:
    d = get_specialist("spark-expert")
    assert d.allowed_tools == [
        "sentinel.spark.analyze_plan", "sentinel.spark.optimize"]


def test_route_keywords() -> None:
    assert route("glue job failed") == ["glue-expert"]
    assert "iceberg-expert" in route("iceberg snapshot expired")
    assert route("???") == ["coordinator"]


def test_plan_tasks_depends_on_chain() -> None:
    tasks = plan_tasks("spark sql issue", {"log": "x.log"})
    kinds = [t.kind for t in tasks]
    assert kinds.count("investigate") >= 2
    assert "validate" in kinds and "synthesize" in kinds
    synth = next(t for t in tasks if t.kind == "synthesize")
    assert synth.depends_on
