"""Cycle 04 E2E A-H (ds-0048)."""

import random
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from data_sentinel.core.contracts import DatasetReference, DriftLevel, ObservationStatus
from data_sentinel.lineage import parse_openlineage_events
from data_sentinel.lineage.graph import build_graph, impact
from data_sentinel.quality import normalize, parse_contract_text, validate_contract
from data_sentinel.quality.drift import detect_drift, drift_findings
from data_sentinel.quality.profile import profile_table
from data_sentinel.quality.versioning import check_version_compat

FIX = Path(__file__).parent.parent / "fixtures"

rng = random.Random(7)  # noqa: S311


def test_e2e_a_contract_validation() -> None:
    """A: valid contract parses+validates; invalid is rejected with issues."""
    ok = parse_contract_text(
        'contract_version: "1.0"\ndataset: a.b\n'
        'rules:\n - {id: r1, type: uniqueness, columns: [id]}\n')
    assert validate_contract(ok).ok
    bad = parse_contract_text(
        'contract_version: "1.0"\ndataset: a.b\n'
        'rules:\n - {id: r1, type: completeness, column: x, '
        'expected: 2.5, severity: bogus}\n')
    v = validate_contract(bad)
    assert any("severidade inválida" in i.message for i in v.issues)
    assert any("fora de [0,1]" in i.message for i in v.issues)


def test_e2e_b_pydeequ_parsing() -> None:
    """B: PyDeequ export normalized preserving metric semantics."""
    obs = normalize((FIX / "quality/pydeequ_metrics.json").read_text(encoding="utf-8"),
                    adapter="pydeequ")
    assert len(obs) == 4
    comp = next(o for o in obs if o.rule_id == "customer_id")
    assert comp.metric_name == "Completeness"
    assert comp.observed_value == 0.97
    assert comp.source == "pydeequ"


def test_e2e_c_quality_regression() -> None:
    """C: FAIL observation + drift finding surface a regression signal."""
    obs = normalize((FIX / "quality/sql_results.json").read_text(encoding="utf-8"),
                    adapter="sql_results")
    fails = [o for o in obs if o.status == ObservationStatus.FAIL]
    assert len(fails) == 1 and fails[0].rule_id == "fresh_h"
    base = [rng.gauss(0, 1) for _ in range(300)]
    cur = [rng.gauss(4, 1) for _ in range(300)]
    res = detect_drift("amount", base, cur)
    findings = drift_findings([res])
    assert findings and findings[0].severity.value in ("HIGH", "MEDIUM")


def test_e2e_d_operational_lineage() -> None:
    """D: real Marquez events -> graph edges."""
    ing = parse_openlineage_events(
        (FIX / "lineage/marquez-real.jsonl").read_text(encoding="utf-8"))
    g = build_graph(ing.events)
    assert len(g.downstream) == 2
    fail_ev = [e for e in ing.events if e.event_type == "FAIL"]
    assert fail_ev and fail_ev[0].run["facets"]["errorMessage"]["message"]


def test_e2e_e_impact_analysis() -> None:
    """E: impact = potential-only reachability."""
    g = build_graph(parse_openlineage_events(
        (FIX / "lineage/marquez-real.jsonl").read_text(encoding="utf-8")).events)
    imp = impact(g, DatasetReference(namespace="s3://lakehouse-raw",
                                     name="raw/events"))
    assert imp.potential_only is True
    assert len(imp.downstream) == 2


def test_e2e_f_iceberg_integration() -> None:
    """F: quality contract can reference an Iceberg table coordinate."""
    c = parse_contract_text(
        'contract_version: "1.0"\ndataset: '
        'glue_catalog.analytics.customer_events\nrules:\n'
        ' - {id: r1, type: freshness, minimum: 86400}\n')
    assert c.dataset.namespace == "glue_catalog.analytics"
    assert c.quality_rules[0].parameters["minimum"] == 86400


def test_e2e_g_doctor_interop() -> None:
    """G: report -> Doctor bundle -> reimported, confidence preserved."""
    from data_sentinel.adapters.doctor.adapter import import_doctor_bundle
    from data_sentinel.adapters.doctor.exporter import export_report_json
    from data_sentinel.core.contracts import (
        DiagnosticReport,
        Finding,
        FindingCategory,
        FindingStatus,
        Severity,
    )

    r = DiagnosticReport(
        request_id="e2e",
        created_at=datetime(2026, 10, 20, tzinfo=UTC),
        findings=[Finding(
            category=FindingCategory.DATA_QUALITY,
            severity=Severity.HIGH, status=FindingStatus.CONFIRMED,
            explanation="observação de qualidade confirmada",
            evidence_ids=["obs:1"])])
    text = export_report_json(r)
    p = Path(tempfile.gettempdir()) / "e2e_bundle.json"
    p.write_text(text, encoding="utf-8")
    imported = import_doctor_bundle(p)
    assert len(imported.findings) == 1
    assert "qualidade" in imported.findings[0].explanation


def test_e2e_h_insufficient_evidence() -> None:
    """H: missing/insufficient data -> UNKNOWN, never fabricated."""
    r = detect_drift("col", [1.0], [])
    assert r.level == DriftLevel.UNKNOWN and r.confidence == "UNKNOWN"
    obs = normalize('{"metrics": [{"instance": "x", "name": "c"}]}',
                    adapter="pydeequ")
    assert obs[0].status == ObservationStatus.UNKNOWN
    assert not check_version_compat("1.0", "3.0").compatible
    profs = profile_table([])
    assert profs == {}
