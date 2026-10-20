"""Internal models returned by AWS connectors.

Not wire contracts — they decouple analyzers from boto3 shapes. Public
reports still travel through core/contracts entities.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class GlueJob:
    """Subset of a Glue job definition relevant to diagnostics."""

    name: str
    description: str | None
    glue_version: str | None
    command_name: str | None
    command_script_location: str | None
    role: str | None
    worker_type: str | None
    number_of_workers: int | None
    max_capacity: float | None
    timeout_minutes: int | None
    execution_class: str | None
    security_configuration: str | None
    default_arguments: dict[str, str] = field(default_factory=dict)
    connections: list[str] = field(default_factory=list)
    raw_keys_present: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GlueJobRun:
    """Subset of a Glue job run relevant to diagnostics."""

    job_name: str
    run_id: str
    status: str
    attempt: int | None
    started_on: datetime | None
    completed_on: datetime | None
    execution_time_seconds: int | None
    error_message: str | None
    glue_version: str | None
    worker_type: str | None
    number_of_workers: int | None
    dpu_seconds: float | None
    log_group_name: str | None
    arguments: dict[str, str] = field(default_factory=dict)
    predecessor_run_id: str | None = None


@dataclass(frozen=True)
class LogEvent:
    """One CloudWatch log event."""

    group: str
    stream: str
    timestamp: datetime
    message: str


@dataclass(frozen=True)
class MetricObservation:
    """Normalized CloudWatch metric observation (§4.5).

    quality records provenance: "observed" (returned by the API) —
    fabricated series are never produced.
    """

    namespace: str
    metric_name: str
    dimensions: dict[str, str]
    timestamp: datetime
    value: float
    unit: str
    statistic: str
    source: str
    quality: str
    semantics: str  # "cumulative" | "gauge" | "delta" — never summed across kinds
