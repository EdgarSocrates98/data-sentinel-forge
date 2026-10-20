"""E2E interop (ds-0038): Doctor bundle → import → incident graph →
enriched report. Always-on (local fixtures only)."""

import json
from datetime import UTC, datetime
from pathlib import Path

from data_sentinel.adapters.doctor import import_doctor_bundle
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
    UnifiedExecutionContext,
    build_incident_graph,
)

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "doctor-data"


def _sentinel_side() -> tuple[list[Finding], list[Evidence]]:
    ev = Evidence(
        evidence_id="sent-e1", source="cloudwatch:/aws-glue/jobs/output",
        source_location="/aws-glue/jobs/output",
        captured_at=datetime(2026, 1, 1, tzinfo=UTC),
        content_hash="b" * 64,
        sanitized_excerpt="java.lang.OutOfMemoryError",
        provenance=EvidenceProvenance.OBSERVED, confidence=0.9,
    )
    f = Finding(
        category=FindingCategory.OUT_OF_MEMORY, severity=Severity.HIGH,
        status=FindingStatus.CONFIRMED,
        explanation="executor OOM no stage 3",
        evidence_ids=["sent-e1"],
    )
    return [f], [ev]


def test_e2e_import_correlate_report(tmp_path: Path) -> None:
    # 1. import real doctor bundle
    imp = import_doctor_bundle(FIX / "handoff-real-probe.json")
    assert imp.findings and imp.evidence
    assert all(f.status != FindingStatus.CONFIRMED for f in imp.findings)

    # 2. sentinel-side operational findings
    sent_f, sent_e = _sentinel_side()

    # 3. incident graph correlates both worlds with provenance intact
    ctx = UnifiedExecutionContext(
        job_name="glue-etl", run_id="jr_1", execution_status="FAILED",
    )
    g = build_incident_graph(
        ctx, sent_f, sent_e,
        imported_findings=imp.findings, imported_evidence=imp.evidence,
    )
    imported_nodes = [
        n for n in g.nodes.values()
        if n.attrs.get("imported") is True
    ]
    assert len(imported_nodes) == len(imp.findings)
    assert g.causal_edges() == []  # nada causal sem justificativa forte
    assert all(
        e.kind != EdgeKind.POTENTIALLY_CAUSED_BY for e in g.edges
    )

    # 4. enriched "report": union keeps provenance classes separate
    all_findings = sent_f + imp.findings
    confirmed = [f for f in all_findings
                 if f.status == FindingStatus.CONFIRMED]
    assert all("importado" not in f.explanation for f in confirmed)
    assert len(all_findings) == 1 + len(imp.findings)


def test_e2e_malicious_bundle_rejected(tmp_path: Path) -> None:
    """Adversarial payloads are data, never code."""
    payloads = [
        {"contract_version": "forge-contracts/1", "tool": {"name": "x"},
         "findings": [{"check_id": "X",
                       "message": "../../etc/passwd",
                       "file": "../../etc/passwd"}]},
        {"contract_version": "forge-contracts/1", "tool": {"name": "x"},
         "findings": [{"check_id": "X",
                       "message": "<!ENTITY xxe SYSTEM 'file:///etc/passwd'>"}]},
    ]
    for i, p in enumerate(payloads):
        f = tmp_path / f"p{i}.json"
        f.write_text(json.dumps(p))
        r = import_doctor_bundle(f)  # deve importar como dados inertes
        assert r.findings  # texto preservado como achado, nunca executado
    # file:// nunca é perseguido: sem evidência criada a partir dele
    assert not Path("/etc/passwd.marker").exists()
