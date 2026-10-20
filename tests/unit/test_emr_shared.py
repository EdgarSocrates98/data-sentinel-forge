"""Shared Spark intelligence tests (ds-0064)."""

from datetime import UTC, datetime, timedelta

from data_sentinel.analyzers.emr.compare import compare
from data_sentinel.analyzers.emr.metrics import (
    TimelineEvent,
    build_incident_timeline,
    mergeable,
    normalize_metric,
)
from data_sentinel.core.contracts.emr import (
    EMRExecutionContext,
    EMRPlatform,
    EMRResourceObservation,
    MetricValue,
)


def test_compare_never_claims_superiority() -> None:
    ctx = [
        EMRExecutionContext(platform=EMRPlatform.EMR_EC2,
                            spark_version="3.5"),
        EMRExecutionContext(platform=EMRPlatform.EMR_SERVERLESS,
                            spark_version="3.4"),
    ]
    obs = [
        EMRResourceObservation(metrics=[
            MetricValue(name="duration_ms", value=100, unit="ms")]),
        EMRResourceObservation(metrics=[
            MetricValue(name="duration_ms", value=80, unit="ms")]),
    ]
    r = compare(ctx, obs)
    assert "NÃO concluir superioridade" in r.verdict
    assert any("versões" in lim for lim in r.limitations)


def test_compare_mismatched_units_flagged() -> None:
    ctx = [EMRExecutionContext(platform=EMRPlatform.EMR_EC2),
           EMRExecutionContext(platform=EMRPlatform.EMR_EKS)]
    obs = [EMRResourceObservation(metrics=[
            MetricValue(name="shuffle_gb", value=5, unit="gb")]),
           EMRResourceObservation(metrics=[
            MetricValue(name="shuffle_gb", value=5000, unit="mb")])]
    r = compare(ctx, obs)
    assert any(not n.comparable for n in r.notes)


def test_metric_merge_semantics() -> None:
    a = normalize_metric({"name": "cpu", "value": 1, "unit": "cores"},
                         platform="emr_ec2", source="cw")
    b = normalize_metric({"name": "cpu", "value": 2, "unit": "cores"},
                         platform="emr_eks", source="cw")
    c = normalize_metric({"name": "cpu", "value": 3, "unit": "pct"},
                         platform="emr_ec2", source="cw")
    assert mergeable(a, b)
    assert not mergeable(a, c)


def test_timeline_temporal_never_causal() -> None:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    evs = [
        TimelineEvent(at=t0, kind="step", label="step start"),
        TimelineEvent(at=t0 + timedelta(minutes=30), kind="executor",
                      label="executor lost"),
        TimelineEvent(at=None, kind="job", label="sem data"),
    ]
    out = build_incident_timeline(evs)
    assert out["undated_count"] == 1
    assert out["gaps"]
    assert all(e["association"] == "temporal" for e in out["events"])
    assert "não é causa" in out["limitations"][0]
