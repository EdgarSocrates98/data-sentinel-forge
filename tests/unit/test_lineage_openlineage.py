"""OpenLineage ingestion tests (ds-0044) — includes REAL Marquez capture."""

import json
from pathlib import Path

from data_sentinel.core.contracts import LineageKind
from data_sentinel.lineage import parse_openlineage_events

FIX = Path(__file__).parent.parent / "fixtures" / "lineage"


def test_real_marquez_jsonl() -> None:
    """Events POSTed to a real Marquez Docker instance (PROVENANCE.json)."""
    text = (FIX / "marquez-real.jsonl").read_text()
    ing = parse_openlineage_events(text, provenance="marquez-real")
    assert len(ing.events) == 4
    assert ing.kind == LineageKind.OBSERVED
    types = [e.event_type for e in ing.events]
    assert types == ["START", "COMPLETE", "START", "FAIL"]
    ev = ing.events[0]
    assert ev.job["name"] == "glue.etl.customer_events"
    assert ev.inputs[0].namespace == "s3://lakehouse-raw"
    assert ev.outputs[0].name == "analytics/customer_events"
    assert ev.event_time is not None
    assert ev.provenance == "marquez-real"


def test_column_lineage_facet_preserved() -> None:
    text = (FIX / "marquez-real.jsonl").read_text()
    ev = parse_openlineage_events(text).events[0]
    raw_out = ev.facets["_raw_outputs"][0]
    cl = raw_out["facets"]["columnLineage"]["fields"]
    assert "customer_id" in cl
    assert cl["total"]["inputFields"][0]["field"] == "amount"


def test_single_event_object() -> None:
    ev = json.loads((FIX / "marquez-real.jsonl").read_text().splitlines()[0])
    ing = parse_openlineage_events(json.dumps(ev))
    assert len(ing.events) == 1


def test_batch_envelope() -> None:
    evs = [json.loads(ln) for ln in
           (FIX / "marquez-real.jsonl").read_text().splitlines()[:2]]
    ing = parse_openlineage_events(json.dumps({"events": evs}))
    assert len(ing.events) == 2


def test_declared_kind() -> None:
    ing = parse_openlineage_events(
        '{"eventType":"OTHER","job":{"name":"j"},"run":{"runId":"r"}}',
        declared=True)
    assert ing.kind == LineageKind.STATIC


def test_malformed_lines_rejected() -> None:
    ing = parse_openlineage_events(
        '{"eventType":"START","run":{"runId":"a"}}\n{bad json}\n{"no_type":1}')
    assert len(ing.events) == 1
    assert ing.rejected == 2
    assert any("rejeitados" in ln for ln in ing.limitations)


def test_empty() -> None:
    ing = parse_openlineage_events("   ")
    assert not ing.events
    assert ing.limitations
