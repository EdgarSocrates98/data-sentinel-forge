"""Sentinel -> Doctor export (ds-0046, §8).

Converts a DiagnosticReport into an ExternalDiagnosticBundle in the
forge-contracts/1 vocabulary so Doctor/Forge can consume Sentinel's
OBSERVED findings. Findings keep Sentinel's status/severity verbatim —
import side decides confidence mapping.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from data_sentinel.core.contracts.interop import (
    ExternalDiagnosticBundle,
    IntegrityMetadata,
    InteropEvidence,
    InteropFinding,
    ToolRef,
)

if TYPE_CHECKING:
    from data_sentinel.core.contracts import DiagnosticReport

EXPORTER_VERSION = "1.0.0"
CONTRACT_TAG = "forge-contracts/1"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _evidence_for(evid: str, source: str) -> InteropEvidence:
    kind, _, ref = evid.partition(":")
    return InteropEvidence(kind=kind or "diagnostic",
                           ref=ref or evid, source=source)


def export_report(report: DiagnosticReport, *, source_ref: str = "",
                  producer_version: str = "0.4.0"
                  ) -> ExternalDiagnosticBundle:
    findings: list[InteropFinding] = []
    evidences: list[InteropEvidence] = []
    for i, f in enumerate(report.findings):
        fid = f"sentinel-{i}"
        ev_ids = []
        for j, ev in enumerate(f.evidence_ids):
            evid = f"{fid}-ev{j}"
            evidences.append(InteropEvidence(
                kind="observed", ref=ev,
                source="data-sentinel",
                detail=f"status={f.status.value}"))
            ev_ids.append(evid)
        findings.append(InteropFinding(
            check_id=fid,
            id=fid,
            title=f"{f.category.value}:{f.severity.value}",
            message=f.explanation,
            severity=f.severity.value,
            confidence=f.status.value,  # verbatim CONFIRMED/PROBABLE/...
            category=f.category.value,
            evidence=[InteropEvidence(kind="observed", ref=r,
                                      source="data-sentinel")
                      for r in f.evidence_ids],
            recommendation="; ".join(f.recommendations),
            source="data-sentinel",
            tags=["sentinel", "observed", f.category.value],
            fingerprint=_sha(fid + f.explanation)[:16],
            unknowns=[{"fact": a} for a in f.alternatives],
        ))

    bundle = ExternalDiagnosticBundle(
        contract_version=CONTRACT_TAG,
        producer=ToolRef(name="data-sentinel", version=producer_version),
        source_references=[source_ref] if source_ref else [],
        findings=findings,
        evidence=evidences,
        summary={
            "finding_count": len(findings),
            "report_id": getattr(report, "report_id", "") or "",
        },
        limitations=[
            *(getattr(report, "limitations", []) or []),
            "export only — Sentinel não executa nada no consumidor",
            "confidence = status observado; Doctor deve manter "
            "proveniência"],
    )
    payload = json.dumps(bundle.model_dump(exclude={"integrity"},
                                         mode="json"),
                         sort_keys=True)
    bundle.integrity = IntegrityMetadata(
        content_sha256=_sha(payload), byte_size=len(payload.encode()))
    return bundle


def export_report_json(report: DiagnosticReport, **kw: Any) -> str:
    return export_report(report, **kw).model_dump_json(indent=2)
