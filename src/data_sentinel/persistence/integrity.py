"""§2.3 — investigation integrity verification.

Confere referências pendentes SEM fabricar: dangling evidence_ids,
ausência de provenance/timeline, hash ausente. Retorna issues
explícitos — nunca repara silenciosamente.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from data_sentinel.core.contracts.agent import InvestigationReport


@dataclass
class IntegrityIssue:
    kind: str            # dangling_evidence | missing_provenance |
    # missing_hash | missing_timeline | unvalidated_finding
    message: str
    entity_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "message": self.message,
                "entity_id": self.entity_id}


@dataclass
class IntegrityReport:
    ok: bool = True
    issues: list[IntegrityIssue] = field(default_factory=list)

    def add(self, kind: str, message: str,
            entity_id: str | None = None) -> None:
        self.ok = False
        self.issues.append(IntegrityIssue(kind, message, entity_id))

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok,
                "issues": [i.to_dict() for i in self.issues]}


def check_report_integrity(
    report: InvestigationReport,
) -> IntegrityReport:
    """Verifica referências internas do relatório investigativo."""
    out = IntegrityReport()
    ev_ids = {e.evidence_id for e in report.evidence}
    f_ids = {f.finding_id for f in report.findings}

    for f in report.findings:
        dangling = [e for e in f.evidence_ids if e not in ev_ids]
        if dangling:
            out.add(
                "dangling_evidence",
                f"finding {f.finding_id} referencia evidência "
                f"ausente {dangling} — sinalizar explicitamente",
                f.finding_id)
        if not f.evidence_ids and str(f.status) in (
                "CONFIRMED", "FindingStatus.CONFIRMED"):
            out.add(
                "unvalidated_finding",
                f"finding CONFIRMED sem evidence_ids: "
                f"{f.finding_id}",
                f.finding_id)

    for e in report.evidence:
        if not getattr(e, "evidence_id", None):
            out.add("missing_hash", "evidence sem id", None)
        prov = getattr(e, "provenance", None) or \
            getattr(e, "source", None)
        if not prov:
            out.add("missing_provenance",
                    f"evidence {e.evidence_id} sem proveniência",
                    e.evidence_id)

    for h in report.hypotheses_supported + report.hypotheses_refuted:
        refs = getattr(h, "evidence_ids", []) or \
            getattr(h, "finding_ids", [])
        bad = [r for r in refs
               if r not in ev_ids and r not in f_ids]
        if bad:
            out.add(
                "dangling_evidence",
                f"hypothesis referencia ids ausentes {bad}",
                getattr(h, "hypothesis_id", None))

    if "timeline" not in report.context and report.findings:
        out.add("missing_timeline",
                "findings sem timeline no contexto — declarar "
                "explicitamente")

    return out
