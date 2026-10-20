"""Incident graph + unified context + timeline tests (ds-0034)."""

from datetime import UTC, datetime

import pytest

from data_sentinel.core.contracts import (
    Evidence,
    EvidenceProvenance,
    Finding,
    FindingCategory,
    FindingStatus,
    Severity,
)
from data_sentinel.diagnostics.incident import (
    EdgeKind,
    NodeKind,
    UnifiedExecutionContext,
    build_incident_graph,
    context_from_hints,
)
from data_sentinel.diagnostics.timeline import (
    EventKind,
    IncidentTimeline,
    TimelineEntry,
    merge_timelines,
)


def _evidence(eid: str = "e1") -> Evidence:
    return Evidence(
        evidence_id=eid,
        source="cloudwatch:/aws-glue/jobs/output",
        source_location="/aws-glue/jobs/output",
        captured_at=datetime(2026, 1, 1, tzinfo=UTC),
        content_hash="a" * 64,
        sanitized_excerpt="java.lang.OutOfMemoryError",
        provenance=EvidenceProvenance.OBSERVED,
        confidence=0.9,
    )


def _finding(eids: list[str], category: FindingCategory = FindingCategory.OUT_OF_MEMORY) -> Finding:
    return Finding(
        category=category,
        severity=Severity.HIGH,
        status=FindingStatus.CONFIRMED,
        explanation="executor OOM",
        evidence_ids=eids,
    )


def test_context_partial_fields_unknown() -> None:
    ctx = context_from_hints({"job_name": "j1", "run_id": "r1",
                              "nonsense_field": "x"})
    assert ctx.job_name == "j1" and ctx.runtime == ""
    assert "runtime" in ctx.unknown_fields()
    assert set(ctx.known_fields()) == {"job_name", "run_id"}


def test_graph_builds_with_justified_edges() -> None:
    ctx = UnifiedExecutionContext(
        job_name="glue-etl", run_id="jr_123", log_stream="ls-1",
        table="orders", database="sales", catalog="glue",
        stage_id="7", execution_status="FAILED",
    )
    f = _finding(["e1"])
    g = build_incident_graph(ctx, [f], [_evidence()])
    kinds = {n.kind for n in g.nodes.values()}
    assert {NodeKind.JOB_RUN, NodeKind.LOG_EVENT, NodeKind.SPARK_STAGE,
            NodeKind.TABLE, NodeKind.CATALOG,
            NodeKind.DIAGNOSTIC_FINDING} <= kinds
    for e in g.edges:
        assert e.justification  # toda aresta tem vínculo
    justs = {e.justification.split("=")[0] for e in g.edges}
    assert "log_stream" in justs and "stage_id" in justs


def test_no_job_context_records_limitation() -> None:
    g = build_incident_graph(UnifiedExecutionContext(), [], [])
    assert any("JobRun" in lim for lim in g.limitations)


def test_edge_without_justification_refused() -> None:
    ctx = UnifiedExecutionContext(job_name="j", run_id="r")
    g = build_incident_graph(ctx, [], [])
    g.add_node(NodeKind.TABLE, "x", node_id="table:x")
    edge = g.add_edge("jobrun:j:r", "table:x", EdgeKind.REFERENCED, "")
    assert edge is None
    assert any("sem vínculo" in lim for lim in g.limitations)


def test_edge_to_missing_node_dropped() -> None:
    g = build_incident_graph(UnifiedExecutionContext(job_name="j"), [], [])
    assert g.add_edge("jobrun:j:", "nó-inexistente", EdgeKind.PRODUCED, "x") is None


def test_imported_findings_never_causal() -> None:
    ctx = UnifiedExecutionContext(job_name="j", run_id="r", table="t")
    imp = Finding(
        category=FindingCategory.CONFIGURATION,
        severity=Severity.MEDIUM,
        status=FindingStatus.PROBABLE,
        explanation="[importado:doctor] config estática",
        evidence_ids=["imp-e"],
    )
    imp_ev = _evidence("imp-e")
    g = build_incident_graph(ctx, [], [],
                             imported_findings=[imp],
                             imported_evidence=[imp_ev])
    assert g.causal_edges() == []
    assert all(e.kind != EdgeKind.POTENTIALLY_CAUSED_BY for e in g.edges)
    assert g.nodes["finding:" + imp.finding_id].attrs["imported"] is True


def test_causal_vs_association_separation() -> None:
    g = build_incident_graph(UnifiedExecutionContext(job_name="j"), [], [])
    g.add_node(NodeKind.JOB_RUN, "j", node_id="j")
    g.add_node(NodeKind.LOG_EVENT, "e", node_id="e")
    g.add_edge("e", "j", EdgeKind.POTENTIALLY_CAUSED_BY, "excecao primária")
    g.add_edge("e", "j", EdgeKind.ASSOCIATED_WITH, "mesmo run_id")
    assert len(g.causal_edges()) == 1
    assert len(g.association_edges()) == 1


def _ts(m: int) -> datetime:
    return datetime(2026, 1, 1, 10, m, tzinfo=UTC)


def test_timeline_gaps_declared() -> None:
    tl = IncidentTimeline(entries=[
        TimelineEntry(_ts(0), "início", None, 1, EventKind.EXECUTION_START),
        TimelineEntry(_ts(10), "falha", "OOM", 2, EventKind.EXCEPTION),
    ])
    tl.detect_gaps()
    assert len(tl.gaps) == 1 and tl.gaps[0].seconds == 600
    assert "gap de 600s" in tl.render()


def test_merge_timelines_sources_noted() -> None:
    a = IncidentTimeline(entries=[
        TimelineEntry(_ts(1), "ev1", None, 1, source="cloudwatch-log")])
    b = IncidentTimeline(entries=[
        TimelineEntry(_ts(2), "ev2", None, 1, source="doctor-bundle")])
    m = merge_timelines(a, b)
    assert [e.summary for e in m.entries] == ["ev1", "ev2"]
    assert any("fontes múltiplas" in n for n in m.granularity_notes)


@pytest.mark.parametrize("msg,exc,expected", [
    ("java.lang.OutOfMemoryError", "OutOfMemoryError", EventKind.EXCEPTION),
    ("WARN memory pressure", None, EventKind.WARNING),
    ("stage 3 failed", None, EventKind.FAILURE),
    ("stage 3 finished", None, EventKind.STAGE),
    ("reading input", None, EventKind.GENERIC),
])
def test_event_classification(msg: str, exc: str | None, expected: EventKind) -> None:
    from data_sentinel.diagnostics.timeline import _classify
    assert _classify(msg, exc) == expected
