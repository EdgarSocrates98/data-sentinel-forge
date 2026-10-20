"""Unified Spark comparison (ds-0064, §6.3).

Compare executions across EMR modalities ONLY when metrics/units are
comparable. Never claims one modality is "more efficient" without
workload/version/resource control — differences are reported with the
control variables that would be needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from data_sentinel.core.contracts.emr import EMRExecutionContext, EMRResourceObservation

_COMPARABLE = {"duration_ms", "vcpu_hours", "memory_gb_hours",
               "shuffle_gb", "spill_gb", "gc_ms"}


@dataclass
class ComparisonNote:
    metric: str
    per_platform: dict[str, float]
    comparable: bool
    caveat: str = ""


@dataclass
class SparkComparison:
    notes: list[ComparisonNote] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    verdict: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"notes": [n.__dict__ for n in self.notes],
                "limitations": self.limitations,
                "verdict": self.verdict}


def compare(contexts: list[EMRExecutionContext],
            observations: list[EMRResourceObservation]
            ) -> SparkComparison:
    """Pair contexts[i] with observations[i]; compare honest metrics."""
    res = SparkComparison()
    if len(contexts) != len(observations):
        res.limitations.append(
            "contextos e observações não pareados — comparação "
            "recusada em vez de inventar")
        return res
    if len(contexts) < 2:
        res.limitations.append("menos de 2 execuções — nada a comparar")
        return res

    platforms = [c.platform.value for c in contexts]
    versions = [c.spark_version or "?" for c in contexts]
    labels = [f"{p}@{v}" for p, v in zip(platforms, versions, strict=True)]

    all_metrics: set[str] = set()
    for o in observations:
        all_metrics.update(m.name for m in o.metrics)
    for name in sorted(all_metrics & _COMPARABLE):
        per: dict[str, float] = {}
        units: set[str] = set()
        for label, obs in zip(labels, observations, strict=True):
            m = obs.get(name)
            if m and m.value is not None:
                per[label] = m.value
                units.add(m.unit or "")
        if len(per) < 2:
            continue
        comparable = len(units) <= 1
        res.notes.append(ComparisonNote(
            metric=name, per_platform=per, comparable=comparable,
            caveat=("" if comparable else
                    f"unidades divergentes {sorted(units)} — não "
                    "comparar diretamente")))

    diff_spark = len(set(versions)) > 1
    if diff_spark:
        res.limitations.append(
            f"versões Spark divergentes {sorted(set(versions))} — "
            "diferenças podem ser da versão, não da modalidade")
    res.verdict = (
        "comparação parcial — workload, versão e recursos não "
        "controlados; NÃO concluir superioridade de modalidade"
        if res.notes else
        "sem métricas comparáveis — nenhuma conclusão")
    return res
