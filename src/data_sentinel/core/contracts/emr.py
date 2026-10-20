"""EMR domain contracts (ds-0060, §2).

Canonical model for the three EMR modalities. Findings reuse the
existing Finding/Evidence contracts — no parallel hierarchy (§2.4).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from data_sentinel.core.contracts.entities import ContractModel, UTCDateTime
from data_sentinel.core.contracts.enums import EvidenceProvenance


class EMRPlatform(StrEnum):
    """§2.1 — the three EMR deployment modalities."""

    EMR_EC2 = "emr_ec2"
    EMR_SERVERLESS = "emr_serverless"
    EMR_EKS = "emr_eks"


class EMRExecutionContext(ContractModel):
    """§2.2 — identifies an EMR execution across modalities.

    Optional fields stay None when not applicable — never invented.
    """

    platform: EMRPlatform
    region: str | None = None
    account_id: str | None = None
    release_label: str | None = None
    spark_version: str | None = None
    engine: str | None = None           # spark|hive|presto|...
    execution_id: str | None = None     # step id / job run id
    application_id: str | None = None
    cluster_id: str | None = None       # j-xxx (EC2)
    virtual_cluster_id: str | None = None  # EKS
    step_id: str | None = None
    namespace: str | None = None        # EKS
    execution_role: str | None = None
    started_at: UTCDateTime | None = None
    completed_at: UTCDateTime | None = None
    status: str | None = None
    source: str | None = None           # api|log|manifest|fixture
    provenance: EvidenceProvenance = EvidenceProvenance.DECLARED


class MetricValue(ContractModel):
    """One observed metric — §2.3 requires origin/unit/timestamp."""

    name: str = Field(min_length=1)
    value: float | None = None
    unit: str | None = None             # cores|mb|gb|count|percent|ms
    source: str | None = None           # cloudwatch|yarn|spark|declared
    captured_at: UTCDateTime | None = None


class EMRResourceObservation(ContractModel):
    """§2.3 — observed resources of an EMR execution."""

    metrics: list[MetricValue] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

    def get(self, name: str) -> MetricValue | None:
        return next((m for m in self.metrics if m.name == name), None)


@runtime_checkable
class EMRAdapter(Protocol):
    """§2.5 — unified adapter protocol.

    Implementations declare real capabilities; operations that do not
    exist on a platform return None/limitations, never a fake shape.
    """

    @property
    def platform(self) -> EMRPlatform: ...

    @property
    def capabilities(self) -> set[str]: ...

    def inspect_execution(self, execution_id: str
                          ) -> EMRExecutionContext | None: ...

    def list_executions(self, **filters: Any
                        ) -> list[EMRExecutionContext]: ...

    def inspect_environment(self) -> dict[str, Any]: ...

    def collect_logs(self, execution_id: str) -> list[str]: ...

    def collect_metrics(self, execution_id: str
                        ) -> EMRResourceObservation: ...

    def collect_spark_artifacts(self, execution_id: str
                              ) -> dict[str, Any]: ...

    def assess_configuration(self) -> dict[str, Any]: ...

    def normalize_evidence(self, raw: dict[str, Any]
                           ) -> dict[str, Any]: ...
