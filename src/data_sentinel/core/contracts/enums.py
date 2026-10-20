"""Controlled enums for Data Sentinel public contracts."""

from enum import StrEnum


class AnalysisMode(StrEnum):
    """Analysis depth profile (§6)."""

    ECONOMY = "economy"
    BALANCED = "balanced"
    DEEP = "deep"
    OFFLINE = "offline"


class EvidenceProvenance(StrEnum):
    """How a piece of evidence was obtained (§2.4)."""

    DECLARED = "declared"
    STATIC_INFERRED = "static_inferred"
    OBSERVED = "observed"


class ExecutionStatus(StrEnum):
    """Status of a job execution described by ExecutionMetadata."""

    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class FindingCategory(StrEnum):
    """Classification of a finding's technical domain."""

    OUT_OF_MEMORY = "out_of_memory"
    DISK_SPACE = "disk_space"
    DATA_SKEW = "data_skew"
    CONFIGURATION = "configuration"
    PERMISSIONS = "permissions"
    NETWORK_IO = "network_io"
    DEPENDENCY = "dependency"
    TIMEOUT = "timeout"
    EXECUTOR_LOSS = "executor_loss"
    SQL_ANTIPATTERN = "sql_antipattern"
    DATA_QUALITY = "data_quality"
    COST = "cost"
    SECURITY = "security"
    UNKNOWN = "unknown"


class FindingStatus(StrEnum):
    """Certainty taxonomy for findings (§2.1)."""

    CONFIRMED = "CONFIRMED"
    PROBABLE = "PROBABLE"
    POSSIBLE = "POSSIBLE"
    UNKNOWN = "UNKNOWN"


class Platform(StrEnum):
    """Execution platform an artifact or workload belongs to."""

    SPARK = "spark"
    AWS_GLUE = "aws_glue"
    DATABRICKS = "databricks"
    TRINO = "trino"
    ATHENA = "athena"
    ICEBERG = "iceberg"
    GENERIC = "generic"


class Severity(StrEnum):
    """Impact severity of a finding or recommendation."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourceType(StrEnum):
    """Kind of input artifact described by a DiagnosticRequest."""

    LOG = "log"
    SQL_QUERY = "sql_query"
    SPARK_EVENT_LOG = "spark_event_log"
    PHYSICAL_PLAN = "physical_plan"
    METRICS = "metrics"
    CONFIG = "config"
    SPARK_PLAN = "spark_plan"
    GLUE_JOB = "glue_job"
    CLOUDWATCH_LOG = "cloudwatch_log"
    OTHER = "other"
