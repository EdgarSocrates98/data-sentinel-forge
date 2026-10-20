"""OpenLineage event ingestion (ds-0044, §6.1-§6.3).

Accepts: a JSONL stream of events, a single event object, or
{"events": [...]}. Preserves raw facet provenance, normalizes to
LineageEvent contracts, marks observed-vs-declared via eventType.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC
from typing import Any

from data_sentinel.core.contracts import (
    DatasetReference,
    LineageEvent,
    LineageKind,
    UTCDateTime,
)

MAX_EVENTS = 100_000

_RUNTIME_TYPES = {"START", "RUNNING", "COMPLETE", "FAIL", "ABORT"}
_DECLARED_TYPES = {"OTHER"}


@dataclass
class IngestedLineage:
    events: list[LineageEvent] = field(default_factory=list)
    kind: LineageKind = LineageKind.OBSERVED
    limitations: list[str] = field(default_factory=list)
    rejected: int = 0


def _ts(raw: Any) -> UTCDateTime | None:
    from datetime import datetime
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except ValueError:
        return None


def _dataset(raw: Any) -> DatasetReference | None:
    if not isinstance(raw, dict):
        return None
    ns, name = raw.get("namespace"), raw.get("name")
    if not name:
        return None
    return DatasetReference(namespace=str(ns or ""), name=str(name))


def _event(raw: dict[str, Any], idx: int, provenance: str
           ) -> LineageEvent | None:
    etype = str(raw.get("eventType") or "")
    if not etype:
        return None
    inputs = [d for d in (_dataset(i) for i in raw.get("inputs") or [])
              if d]
    outputs = [d for d in (_dataset(o) for o in raw.get("outputs") or [])
               if d]
    run = raw.get("run") or {}
    job = raw.get("job") or {}
    return LineageEvent(
        event_id=str(run.get("runId") or f"event-{idx}"),
        event_type=etype,
        event_time=_ts(raw.get("eventTime")),
        run={"runId": str(run.get("runId") or ""),
             "facets": run.get("facets") or {}},
        job={"namespace": str(job.get("namespace") or ""),
             "name": str(job.get("name") or ""),
             "facets": job.get("facets") or {}},
        inputs=inputs,
        outputs=outputs,
        facets={
            "_raw_inputs": raw.get("inputs") or [],
            "_raw_outputs": raw.get("outputs") or [],
        },
        provenance=provenance,
    )


def parse_openlineage_events(text: str, *, provenance: str = "",
                             declared: bool = False
                             ) -> IngestedLineage:
    """Parse JSONL/batch/single OpenLineage payload."""
    events: list[LineageEvent] = []
    rejected = 0
    raws: list[Any] = []
    stripped = text.strip()
    if not stripped:
        return IngestedLineage(kind=LineageKind.OBSERVED, limitations=["payload vazio"])

    parsed_any = False
    try:
        data = json.loads(stripped)
        parsed_any = True
        if isinstance(data, dict) and "events" in data:
            raws = data["events"]
        elif isinstance(data, dict):
            raws = [data]
        elif isinstance(data, list):
            raws = data
    except json.JSONDecodeError:
        pass

    if not parsed_any:
        # JSONL fallback
        for line in stripped.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raws.append(json.loads(line))
            except json.JSONDecodeError:
                rejected += 1

    for i, r in enumerate(raws[:MAX_EVENTS]):
        if not isinstance(r, dict):
            rejected += 1
            continue
        ev = _event(r, i, provenance)
        if ev is None:
            rejected += 1
        else:
            events.append(ev)

    kinds = {e.event_type for e in events}
    kind = (LineageKind.STATIC if declared
            or not kinds & _RUNTIME_TYPES else LineageKind.OBSERVED)
    limits: list[str] = []
    if rejected:
        limits.append(f"{rejected} eventos rejeitados (malformados)")
    if not events:
        limits.append("nenhum evento válido — linhagem indisponível")
    if len(raws) > MAX_EVENTS:
        limits.append(f"entrada truncada em {MAX_EVENTS} eventos")
    return IngestedLineage(events=events, kind=kind,
                           limitations=limits, rejected=rejected)
