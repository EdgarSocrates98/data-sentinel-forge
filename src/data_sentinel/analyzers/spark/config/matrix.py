"""Compatibility matrix (§8.1): (spark, glue) x config → status/default/limits.

Statuses: supported | default | unsupported | conditional.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigSpec:
    config: str
    default: str
    supported_spark: tuple[str, ...]
    supported_glue: tuple[str, ...]
    status: str
    limitation: str


_SPARK = ("3.3", "3.4", "3.5")
_GLUE = ("3.0", "4.0", "5.0")

CONFIG_MATRIX: dict[str, ConfigSpec] = {
    "spark.sql.adaptive.enabled": ConfigSpec(
        "spark.sql.adaptive.enabled", "true", _SPARK, ("4.0", "5.0"),
        "supported", "AQE ativo por padrão em Spark 3.2+; Glue 3.0 (Spark 3.1) não suporta.",
    ),
    "spark.sql.shuffle.partitions": ConfigSpec(
        "spark.sql.shuffle.partitions", "200", _SPARK, _GLUE,
        "supported", "Default 200 frequentemente inadequado — nem sempre errado.",
    ),
    "spark.sql.autoBroadcastJoinThreshold": ConfigSpec(
        "spark.sql.autoBroadcastJoinThreshold", "10MB", _SPARK, _GLUE,
        "supported", "Threshold alto sem memória de executor suficiente gera OOM.",
    ),
    "spark.sql.adaptive.coalescePartitions.enabled": ConfigSpec(
        "spark.sql.adaptive.coalescePartitions.enabled", "true", _SPARK, ("4.0", "5.0"),
        "conditional", "Requer spark.sql.adaptive.enabled=true.",
    ),
    "spark.sql.adaptive.skewJoin.enabled": ConfigSpec(
        "spark.sql.adaptive.skewJoin.enabled", "true", _SPARK, ("4.0", "5.0"),
        "conditional", "Requer AQE; só atua em sort-merge joins com skew detectável.",
    ),
    "spark.sql.files.maxPartitionBytes": ConfigSpec(
        "spark.sql.files.maxPartitionBytes", "128MB", _SPARK, _GLUE,
        "supported", "Afeta leitura de arquivos; não se aplica a JDBC.",
    ),
    "spark.executor.memory": ConfigSpec(
        "spark.executor.memory", "1g", _SPARK, _GLUE,
        "supported", "Aumento tem implicações de custo/quota — avaliar disponibilidade.",
    ),
    "spark.executor.cores": ConfigSpec(
        "spark.executor.cores", "1", _SPARK, _GLUE,
        "supported", "Glue mapeia para worker types — checar compatibilidade do worker.",
    ),
    "spark.driver.memory": ConfigSpec(
        "spark.driver.memory", "1g", _SPARK, _GLUE,
        "supported", "Driver OOM é comum com collect/broadcast grandes.",
    ),
    "spark.dynamicAllocation.enabled": ConfigSpec(
        "spark.dynamicAllocation.enabled", "false", _SPARK, _GLUE,
        "conditional", "Glue suporta via --enable-auto-scaling; conflita com executors fixos.",
    ),
    "spark.sql.cbo.enabled": ConfigSpec(
        "spark.sql.cbo.enabled", "false", _SPARK, _GLUE,
        "conditional", "Requer estatísticas coletadas (ANALYZE TABLE); sem stats não muda planos.",
    ),
}


def support_status(config: str, spark: str | None, glue: str | None) -> tuple[str, str]:
    """Return (status, note). missing runtime → ("unknown_runtime", ...)."""
    spec = CONFIG_MATRIX.get(config)
    if spec is None:
        return "not_in_matrix", "configuração fora da matriz §8.1 — sem avaliação"
    if spark is None and glue is None:
        return "unknown_runtime", "runtime não declarado — aplicabilidade indeterminada"
    if glue is not None and glue not in spec.supported_glue:
        return "unsupported", f"não suportada em Glue {glue} ({spec.limitation})"
    if (
        spark is not None
        and glue is None
        and spec.supported_spark
        and spark not in spec.supported_spark
    ):
        return "unsupported", f"não suportada em Spark {spark} ({spec.limitation})"
    return spec.status, spec.limitation
