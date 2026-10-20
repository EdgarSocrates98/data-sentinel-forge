"""Incident evidence graph + unified execution context (Cycle 03.1 §4).

Cross-source operational intelligence: correlates evidence across Glue
metadata, CloudWatch logs/metrics, Spark plans, Iceberg metadata, IAM
context and imported external findings — only via *justifiable* links
(shared job/run/table/stage/task ids, locations or catalog refs), never
by name similarity alone.

Causal edges (POTENTIALLY_CAUSED_BY) are a separate class from temporal
association edges — correlation is never represented as proven causality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from data_sentinel.core.contracts import Evidence, Finding


class NodeKind(StrEnum):
    JOB_RUN = "JobRun"
    LOG_EVENT = "LogEvent"
    SPARK_STAGE = "SparkStage"
    SPARK_TASK = "SparkTask"
    TABLE = "Table"
    CATALOG = "Catalog"
    SNAPSHOT = "Snapshot"
    IAM_PRINCIPAL = "IAMPrincipal"
    PERMISSION_FINDING = "PermissionFinding"
    DIAGNOSTIC_FINDING = "DiagnosticFinding"


class EdgeKind(StrEnum):
    EXECUTED_AS = "EXECUTED_AS"
    PRODUCED = "PRODUCED"
    FAILED_AT = "FAILED_AT"
    REFERENCED = "REFERENCED"
    READ_FROM = "READ_FROM"
    WROTE_TO = "WROTE_TO"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    SUPPORTED_BY = "SUPPORTED_BY"
    POTENTIALLY_CAUSED_BY = "POTENTIALLY_CAUSED_BY"


CAUSAL_EDGES = frozenset({EdgeKind.POTENTIALLY_CAUSED_BY})
ASSOCIATION_EDGES = frozenset(k for k in EdgeKind if k not in CAUSAL_EDGES)


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    kind: NodeKind
    label: str
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    src: str
    dst: str
    kind: EdgeKind
    justification: str  # the shared key that legitimizes the link


@dataclass
class EvidenceGraph:
    """Operational evidence graph with explicit link justifications."""

    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def add_node(
        self, kind: NodeKind, label: str, node_id: str | None = None,
        **attrs: Any,
    ) -> GraphNode:
        nid = node_id or f"{kind.value}:{label}"
        if nid not in self.nodes:
            self.nodes[nid] = GraphNode(node_id=nid, kind=kind, label=label,
                                        attrs=dict(attrs))
        return self.nodes[nid]

    def add_edge(
        self, src: str, dst: str, kind: EdgeKind, justification: str,
    ) -> GraphEdge | None:
        if src not in self.nodes or dst not in self.nodes:
            self.limitations.append(
                f"aresta descartada ({kind.value}): nó ausente "
                f"({src if src not in self.nodes else dst})"
            )
            return None
        if not justification:
            self.limitations.append(
                f"aresta recusada ({kind.value}): sem vínculo justificável"
            )
            return None
        edge = GraphEdge(src=src, dst=dst, kind=kind, justification=justification)
        if edge not in self.edges:
            self.edges.append(edge)
        return edge

    def causal_edges(self) -> list[GraphEdge]:
        return [e for e in self.edges if e.kind in CAUSAL_EDGES]

    def association_edges(self) -> list[GraphEdge]:
        return [e for e in self.edges if e.kind in ASSOCIATION_EDGES]


@dataclass
class UnifiedExecutionContext:
    """§4.1 unified context — absent fields stay UNKNOWN (empty string)."""

    account: str = ""
    region: str = ""
    job_name: str = ""
    run_id: str = ""
    runtime: str = ""
    glue_version: str = ""
    spark_version: str = ""
    iceberg_version: str = ""
    catalog: str = ""
    database: str = ""
    table: str = ""
    log_stream: str = ""
    stage_id: str = ""
    task_id: str = ""
    timestamp: str = ""
    operation: str = ""
    execution_status: str = ""

    def known_fields(self) -> dict[str, str]:
        return {k: v for k, v in self.__dict__.items() if v}

    def unknown_fields(self) -> list[str]:
        return [k for k, v in self.__dict__.items() if not v]


def _safe_str(v: Any) -> str:
    return str(v) if v is not None else ""


def context_from_hints(hints: dict[str, Any]) -> UnifiedExecutionContext:
    """Build context from a heterogeneous hints dict (CLI/metadata)."""
    known = set(UnifiedExecutionContext.__dataclass_fields__)
    return UnifiedExecutionContext(**{
        k: _safe_str(v) for k, v in hints.items() if k in known
    })


def _link_keys(ctx: UnifiedExecutionContext) -> dict[str, str]:
    """Shared keys usable as justifiable cross-source links (§4.4)."""
    keys: dict[str, str] = {}
    for f in ("run_id", "job_name", "table", "database", "catalog",
              "stage_id", "task_id", "log_stream"):
        v = getattr(ctx, f)
        if v:
            keys[f] = v
    return keys


def attach_finding(
    graph: EvidenceGraph,
    finding: Finding,
    evidence: list[Evidence],
    ctx: UnifiedExecutionContext,
    *,
    imported: bool = False,
) -> GraphNode:
    """Attach a diagnostic finding + its evidence to the graph.

    Links to operational nodes only via justifiable shared keys; imported
    findings get ASSOCIATED_WITH (never causal) edges.
    """
    kind = (
        NodeKind.PERMISSION_FINDING
        if finding.category.value == "permissions"
        else NodeKind.DIAGNOSTIC_FINDING
    )
    node = graph.add_node(
        kind, finding.explanation[:80], node_id=f"finding:{finding.finding_id}",
        severity=finding.severity.value, status=finding.status.value,
        imported=imported,
    )
    ev_by_id = {e.evidence_id: e for e in evidence}
    for eid in finding.evidence_ids:
        ev = ev_by_id.get(eid)
        if ev is None:
            continue
        ev_node = graph.add_node(
            NodeKind.LOG_EVENT, ev.source_location[:80],
            node_id=f"evidence:{eid}", provenance=ev.provenance.value,
        )
        graph.add_edge(ev_node.node_id, node.node_id, EdgeKind.SUPPORTED_BY,
                       justification=f"evidence_id={eid}")
    # justifiable context links only
    for key, val in _link_keys(ctx).items():
        for kind_prefix, nk in (
            ("table", NodeKind.TABLE), ("catalog", NodeKind.CATALOG),
            ("database", NodeKind.CATALOG),
        ):
            if key == kind_prefix:
                ref = graph.add_node(nk, val)
                edge_kind = (
                    EdgeKind.ASSOCIATED_WITH if imported else EdgeKind.REFERENCED
                )
                graph.add_edge(node.node_id, ref.node_id, edge_kind,
                               justification=f"{key}={val}")
    return node


def build_incident_graph(
    ctx: UnifiedExecutionContext,
    findings: list[Finding],
    evidence: list[Evidence],
    *,
    imported_findings: list[Finding] | None = None,
    imported_evidence: list[Evidence] | None = None,
) -> EvidenceGraph:
    """Build the operational evidence graph for one incident context."""
    graph = EvidenceGraph()
    if ctx.job_name or ctx.run_id:
        job = graph.add_node(
            NodeKind.JOB_RUN, ctx.job_name or ctx.run_id,
            node_id=f"jobrun:{ctx.job_name}:{ctx.run_id}",
            run_id=ctx.run_id, status=ctx.execution_status,
        )
        if ctx.log_stream:
            ls = graph.add_node(NodeKind.LOG_EVENT, ctx.log_stream,
                                node_id=f"logstream:{ctx.log_stream}")
            graph.add_edge(job.node_id, ls.node_id, EdgeKind.PRODUCED,
                           justification=f"log_stream={ctx.log_stream}")
        if ctx.stage_id:
            st = graph.add_node(NodeKind.SPARK_STAGE, ctx.stage_id,
                                node_id=f"stage:{ctx.stage_id}")
            graph.add_edge(st.node_id, job.node_id, EdgeKind.FAILED_AT,
                           justification=f"stage_id={ctx.stage_id}")
        if ctx.catalog:
            graph.add_node(NodeKind.CATALOG, ctx.catalog,
                           node_id=f"catalog:{ctx.catalog}")
        if ctx.table:
            t = graph.add_node(NodeKind.TABLE, ctx.table,
                               node_id=f"table:{ctx.database}.{ctx.table}")
            if ctx.catalog:
                graph.add_edge(t.node_id, f"catalog:{ctx.catalog}",
                               EdgeKind.REFERENCED,
                               justification=f"catalog={ctx.catalog}")
    else:
        graph.limitations.append(
            "contexto sem job_name/run_id: nó JobRun não criado"
        )
    for f in findings:
        attach_finding(graph, f, evidence, ctx)
    for f in imported_findings or []:
        attach_finding(graph, f, imported_evidence or [], ctx, imported=True)
    return graph
