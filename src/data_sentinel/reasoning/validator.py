"""Evidence validator (§8.3) — independent cross-check of findings.

Verifies project hard rules on the real contract:
- non-UNKNOWN findings require ``evidence_ids``;
- ``FindingStatus.UNKNOWN`` requires declared unknowns
  (``alternatives``, per exporter convention);
- no duplicated claims;
- severity is coherent with status (CRITICAL+UNKNOWN is suspicious).

Never upgrades confidence; only annotates/downgrades.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from data_sentinel.core.contracts.entities import Finding
from data_sentinel.core.contracts.enums import FindingStatus, Severity


@dataclass
class ValidationIssue:
    finding_id: str
    issue: str
    severity: str = "warning"  # warning | error


@dataclass
class ValidationReport:
    checked: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]


_HIGH = {Severity.HIGH, Severity.CRITICAL}


class EvidenceValidator:
    """Deterministic, independent validation of a finding set."""

    def validate(self, findings: list[Finding]) -> ValidationReport:
        rep = ValidationReport(checked=len(findings))
        seen: set[str] = set()
        for f in findings:
            fid = f.finding_id
            if (f.status != FindingStatus.UNKNOWN
                    and not f.evidence_ids):
                rep.issues.append(ValidationIssue(
                    fid, "finding não-UNKNOWN sem evidence_ids", "error"))
            if (f.status == FindingStatus.UNKNOWN
                    and not f.alternatives):
                rep.issues.append(ValidationIssue(
                    fid, "UNKNOWN sem unknowns declarados", "error"))
            if (f.status == FindingStatus.UNKNOWN
                    and f.severity in _HIGH):
                rep.issues.append(ValidationIssue(
                    fid, "severidade alta com status UNKNOWN"))
            key = f"{f.category}:{f.explanation[:80]}".lower()
            if key in seen:
                rep.issues.append(ValidationIssue(
                    fid, "possível duplicata de claim"))
            seen.add(key)
        return rep
