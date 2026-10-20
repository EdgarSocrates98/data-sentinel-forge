"""Lineage graph + impact analysis (ds-0045, §7).

Builds a dataset-level DAG from ingested LineageEvents. Upstream/
downstream traversal is graph-theoretic; impact is reported as
POTENTIAL (graph-reachable) unless corroborated by observed failures —
never promoted to proven impact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from data_sentinel.core.contracts import (
    DatasetReference,
    ImpactAssessment,
    LineageEvent,
)


def _key(d: DatasetReference) -> str:
    return f"{d.namespace}/{d.name}" if d.namespace else d.name


@dataclass
class LineageGraph:
    """dataset -> {outputs (downstream), inputs (upstream)} plus run provenance."""

    downstream: dict[str, set[str]] = field(default_factory=dict)
    upstream: dict[str, set[str]] = field(default_factory=dict)
    nodes: dict[str, DatasetReference] = field(default_factory=dict)
    jobs: dict[str, list[str]] = field(default_factory=dict)  # dataset -> job names
    event_ids: dict[str, list[str]] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)

    def add_event(self, ev: LineageEvent) -> None:
        job = ev.job.get("name") or ""
        for d in (*ev.inputs, *ev.outputs):
            self.nodes[_key(d)] = d
        in_keys = {_key(i) for i in ev.inputs}
        out_keys = {_key(o) for o in ev.outputs}
        for ok in out_keys:
            self.upstream.setdefault(ok, set()).update(in_keys)
            if job:
                self.jobs.setdefault(ok, []).append(job)
            self.event_ids.setdefault(ok, []).append(ev.event_id)
        for ik in in_keys:
            self.downstream.setdefault(ik, set()).update(out_keys)
            if job:
                self.jobs.setdefault(ik, []).append(job)
            self.event_ids.setdefault(ik, []).append(ev.event_id)


def build_graph(events: list[LineageEvent]) -> LineageGraph:
    g = LineageGraph()
    for ev in events:
        g.add_event(ev)
    if not events:
        g.limitations.append("grafo vazio — sem eventos de linhagem")
    return g


def _walk(edges: dict[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        n = stack.pop()
        for m in edges.get(n, ()):
            if m not in seen:
                seen.add(m)
                stack.append(m)
    return seen


def impact(graph: LineageGraph, target: DatasetReference) -> ImpactAssessment:
    """Reachability-based impact — POTENTIAL, labeled as such."""
    t = _key(target)
    up = _walk(graph.upstream, t)
    down = _walk(graph.downstream, t)

    def _ref(k: str) -> DatasetReference:
        ref = graph.nodes.get(k)
        if ref is not None:
            return ref
        return DatasetReference(
            namespace=k.rsplit("/", 1)[0] if "/" in k else "",
            name=k.rsplit("/", 1)[-1])

    return ImpactAssessment(
        target=target,
        upstream=[_ref(k) for k in sorted(up)],
        downstream=[_ref(k) for k in sorted(down)],
        affected_entities=sorted(
            {j for ds in down | up for j in graph.jobs.get(ds, [])}),
        confidence=1.0 if down else 0.0,
        graph_paths=[[t, *sorted(down)]],
        limitations=[
            "impacto = alcançabilidade no grafo (potencial), não prova "
            "de quebra real",
            "linhagem de coluna/filtros pode reduzir o conjunto real",
            *graph.limitations])
