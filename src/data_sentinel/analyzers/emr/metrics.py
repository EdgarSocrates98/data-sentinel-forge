"""Metrics normalization (ds-0064, §7.3) + incident timeline (§7.4).

Canonical metric model; never merges metrics with different semantics.
Timeline correlation is temporal-association only — never causation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import Any


@dataclass(frozen=True)
class CanonicalMetric:
    platform: str
    namespace: str
    name: str
    dimensions: tuple[tuple[str, str], ...]
    value: float | None
    unit: str
    source: str                      # cloudwatch|yarn|spark|k8s|declared
    captured_at: datetime | None = None
    quality: str = "observed"        # observed|declared|estimated


def normalize_metric(raw: dict[str, Any], *,
                     platform: str, source: str) -> CanonicalMetric:
    dims = tuple(sorted(
        (str(k), str(v)) for k, v in
        (raw.get("dimensions") or {}).items()))
    return CanonicalMetric(
        platform=platform,
        namespace=str(raw.get("namespace", "")),
        name=str(raw.get("name", "")),
        dimensions=dims,
        value=(float(raw["value"])
               if isinstance(raw.get("value"), (int, float))
               else None),
        unit=str(raw.get("unit", "")),
        source=source,
        captured_at=raw.get("timestamp"),
        quality=str(raw.get("quality", "observed")))


def mergeable(a: CanonicalMetric, b: CanonicalMetric) -> bool:
    """§7.3 — only same semantics+unit+namespace can be combined."""
    return (a.name == b.name and a.unit == b.unit
            and a.namespace == b.namespace
            and a.dimensions == b.dimensions)


@dataclass
class TimelineEvent:
    at: datetime | None
    kind: str                        # step|stage|executor|infra|job
    label: str
    provenance: str = "declared"
    association: str = "temporal"    # §7.4 — never "causal"


def build_incident_timeline(events: list[TimelineEvent]
                            ) -> dict[str, Any]:
    dated = [e for e in events if e.at is not None]
    undated = [e for e in events if e.at is None]
    dated.sort(key=lambda e: (e.at or datetime.min.replace(tzinfo=UTC), e.kind, e.label))
    gaps: list[str] = []
    for prev, cur in pairwise(dated):
        if prev.at is None or cur.at is None:
            continue
        delta = (cur.at - prev.at).total_seconds()
        if delta > 900:
            gaps.append(f"gap {delta/60:.0f}min entre "
                        f"'{prev.label}' e '{cur.label}'")
    return {
        "events": [{"at": e.at.isoformat() if e.at else None,
                    "kind": e.kind, "label": e.label,
                    "provenance": e.provenance,
                    "association": e.association}
                   for e in dated],
        "undated_count": len(undated),
        "gaps": gaps,
        "limitations": [
            "correlação é temporal apenas — associação não é causa",
            f"{len(undated)} evento(s) sem timestamp descartados",
        ] if undated else [
            "correlação é temporal apenas — associação não é causa"],
    }
