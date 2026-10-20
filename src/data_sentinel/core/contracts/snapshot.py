"""Operational history contracts — ExecutionSnapshot (ds-0082, §3.1).

Snapshots are observations, not facts about production: provenance
declares whether data was collected directly or imported.
"""

from __future__ import annotations

from pydantic import Field

from data_sentinel.core.contracts.entities import ContractModel


class ExecutionSnapshot(ContractModel):
    """Point-in-time observation of one workload execution (§3.1)."""
    snapshot_id: str = Field(min_length=1)
    platform: str = Field(min_length=1)  # glue | emr-ec2 | emr-serverless
    job_id: str | None = None           # | emr-eks | spark | openlineage
    run_id: str | None = None
    runtime: str | None = None          # e.g. glue-version, emr-release
    started_at: str | None = None       # ISO strings; no wall-clock here
    ended_at: str | None = None
    duration_s: float | None = None
    input_bytes: int | None = None
    output_bytes: int | None = None
    resource_metrics: dict[str, float] = Field(default_factory=dict)
    failure: bool | None = None         # None = unknown
    config_fingerprint: str | None = None
    dataset_refs: list[str] = Field(default_factory=list)
    cost_observations: dict[str, float] = Field(default_factory=dict)
    provenance: str = Field(min_length=1)  # "direct" | "imported" | ...
    limitations: list[str] = Field(default_factory=list)


class BaselineKind(ContractModel):
    """Baseline selector (§3.3)."""
    kind: str = Field(min_length=1)  # previous | rolling | median |
    # reference | cohort
    window: int | None = None
    reference_run_id: str | None = None


class ComparisonResult(ContractModel):
    """Output of comparing a snapshot against a baseline (§3.5)."""
    comparable: bool
    incomparability_reasons: list[str] = Field(default_factory=list)
    duration_delta_s: float | None = None
    duration_delta_pct: float | None = None
    resource_deltas: dict[str, float] = Field(default_factory=dict)
    volume_delta_input: int | None = None
    volume_delta_output: int | None = None
    failure_regression: bool | None = None  # True = new failure appeared
    config_drift: list[str] = Field(default_factory=list)
    quality_changes: list[str] = Field(default_factory=list)
    cost_delta: dict[str, float] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
