"""EMR contracts tests (ds-0060)."""

from typing import ClassVar

from data_sentinel.core.contracts import (
    EMRExecutionContext,
    EMRPlatform,
    EMRResourceObservation,
    MetricValue,
)
from data_sentinel.core.contracts.emr import EMRAdapter


def test_platform_values() -> None:
    assert {p.value for p in EMRPlatform} == {
        "emr_ec2", "emr_serverless", "emr_eks"}


def test_context_optional_fields_stay_none() -> None:
    c = EMRExecutionContext(platform=EMRPlatform.EMR_SERVERLESS)
    assert c.cluster_id is None and c.namespace is None
    assert c.provenance.value == "declared"


def test_observation_lookup_by_name() -> None:
    obs = EMRResourceObservation(metrics=[
        MetricValue(name="cpu", value=4, unit="cores",
                    source="declared"),
        MetricValue(name="memory_gb", value=16, unit="gb")])
    assert obs.get("cpu").value == 4
    assert obs.get("missing") is None


def test_adapter_protocol_runtime_check() -> None:
    class Fake:
        platform = EMRPlatform.EMR_EC2
        capabilities: ClassVar[set] = {"inspect_execution"}
        def inspect_execution(self, eid): return None
        def list_executions(self, **f): return []
        def inspect_environment(self): return {}
        def collect_logs(self, eid): return []
        def collect_metrics(self, eid): return None
        def collect_spark_artifacts(self, eid): return {}
        def assess_configuration(self): return {}
        def normalize_evidence(self, raw): return raw
    assert isinstance(Fake(), EMRAdapter)
