"""EMR cost tests (ds-0065)."""

from data_sentinel.analyzers.emr.cost import (
    cost_recommendations,
    estimate_ec2,
    estimate_eks,
    estimate_serverless,
)


def test_serverless_estimate_with_sources() -> None:
    e = estimate_serverless(10.0, mem_gb_hours=64.0)
    assert e.amount and e.amount > 0
    assert e.price_source.startswith("static-table")
    assert e.confidence == "POSSIBLE"
    assert e.assumptions and e.exclusions


def test_missing_usage_is_unknown_not_zero() -> None:
    e = estimate_serverless(None)
    assert e.amount is None and e.confidence == "UNKNOWN"


def test_ec2_unknown_instance_type_honest() -> None:
    e = estimate_ec2("p99.mega", 4, 2.0)
    assert e.amount is None and e.confidence == "UNKNOWN"
    e2 = estimate_ec2("m5xlarge", 4, 2.0)
    assert e2.amount and e2.amount > 0
    assert "ec2" in e2.components and "emr_markup" in e2.components


def test_eks_separates_control_plane() -> None:
    e = estimate_eks(5.0, cluster_hours=24.0)
    assert "eks_control_plane" in e.components
    assert any("EC2" in x for x in e.exclusions)


def test_recommendations_carry_sla_caveat() -> None:
    recs = cost_recommendations([estimate_ec2("m5xlarge", 2, 1.0)])
    assert any("SLA" in r for r in recs)
