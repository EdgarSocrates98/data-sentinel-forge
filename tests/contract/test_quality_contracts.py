"""Contract tests — Cycle 04 quality/lineage/impact models (ds-0040)."""

import pytest
from pydantic import ValidationError

from data_sentinel.core.contracts import (
    DataQualityContract,
    DatasetReference,
    DriftLevel,
    FreshnessPolicy,
    ImpactAssessment,
    LineageEvent,
    ObservationStatus,
    QualityObservation,
    QualityRule,
    RuleType,
)


def _dataset() -> DatasetReference:
    return DatasetReference(namespace="lake.sales", name="orders",
                            platform="glue", catalog="glue")


def test_dataset_reference_minimal() -> None:
    d = _dataset()
    assert d.name == "orders" and d.account == ""


def test_quality_rule_types() -> None:
    r = QualityRule(rule_id="r1", rule_type=RuleType.COMPLETENESS,
                    target="order_id", expected=1.0, severity="high")
    assert r.rule_type == "completeness"
    assert QualityRule(rule_id="r2", rule_type="uniqueness_ratio",
                       target="id").rule_type == RuleType.UNIQUENESS_RATIO


def test_contract_with_alias_schema() -> None:
    c = DataQualityContract.model_validate({
        "contract_id": "dq-orders", "version": "1.0",
        "dataset": _dataset().model_dump(),
        "schema": {"order_id": "long"},
        "quality_rules": [{"rule_id": "r1", "rule_type": "completeness",
                           "target": "order_id"}],
    })
    assert c.schema_fields == {"order_id": "long"}
    dumped = c.model_dump(by_alias=True)
    assert "schema" in dumped


def test_contract_round_trip() -> None:
    c = DataQualityContract(
        contract_id="dq1", version="2.0", dataset=_dataset(),
        freshness_policy=FreshnessPolicy(max_age_seconds=3600),
        owner="data-eng", provenance="repo:contracts/orders.yaml",
    )
    c2 = DataQualityContract.model_validate_json(c.model_dump_json())
    assert c2 == c


def test_observation_unknown_by_default() -> None:
    o = QualityObservation(observation_id="o1", rule_id="r1",
                           dataset=_dataset())
    assert o.status == ObservationStatus.UNKNOWN


def test_lineage_event_tolerates_minimal() -> None:
    e = LineageEvent(event_id="e1", event_type="COMPLETE",
                     run={"runId": "r1"}, job={"name": "j"},
                     inputs=[_dataset()], outputs=[])
    assert e.inputs[0].name == "orders"


def test_impact_assessment_potential_only() -> None:
    a = ImpactAssessment(target=_dataset(), confidence=0.7)
    assert a.potential_only is True


def test_strict_rejection_unknown_field() -> None:
    with pytest.raises(ValidationError):
        QualityRule(rule_id="r", rule_type="completeness",
                    target="x", rogue=True)


def test_enums() -> None:
    assert DriftLevel.HIGH.value == "high"
    assert ObservationStatus.UNKNOWN.value == "UNKNOWN"
