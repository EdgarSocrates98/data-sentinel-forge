"""Deterministic static-Doctor x runtime-Sentinel correlation (lf-0030, PHASE 8).

Correlates findings imported from a Forge Doctor bundle (static,
``EvidenceProvenance.DECLARED``) with findings produced by Sentinel runtime
analyzers (``OBSERVED``/``STATIC_INFERRED``) over **declared keys only** —
never fuzzy text similarity:

1. **subject anchor** — normalized ``Evidence.source_location`` tokens:
   the location stripped of ``:N``/``:N-M`` line suffixes and ``bundle://``
   prefixes, lowercased, separators normalized (``loc:`` key), plus its
   basename (``base:`` key);
2. **category** — ``FindingCategory`` equality.

Match strength (in order):

- ``path+category`` — same normalized location token and same category;
- ``basename+category`` — same basename and same category (weaker: basenames
  collide across directories — reported as such);
- ``path-only`` — same location token but different categories (the two
  producers classified the same artifact differently — kept, marked).

Hard rules:

- Correlated evidence is **not** automatically independent proof — two
  producers naming the same artifact may share an upstream cause.
- Co-occurrence does **not** establish causality — the report asserts no
  direction between a static finding and a runtime finding.
- Correlation never upgrades status: a ``POSSIBLE``/``PROBABLE`` doctor
  finding matched to a Sentinel finding stays exactly what it was. The
  report carries ``no_confirmation_upgrade=True`` as a contract.
- Absent doctor evidence is a first-class outcome — an empty doctor side
  yields ``doctor_absent=True``, not an error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from data_sentinel.core.contracts import Evidence, Finding

DISCLAIMER = (
    "correlated evidence is not automatically independent proof — both "
    "producers may share an upstream cause; co-occurrence does not "
    "establish causality; each side keeps its own status, severity, "
    "confidence and provenance — correlation upgrades nothing"
)

_LINE_SUFFIX = re.compile(r":\d+(?:-\d+)?$")
_BUNDLE_PREFIX = re.compile(r"^bundle://[^/]+/")


def _norm_location(location: str) -> str:
    """Normalize a source_location into a comparable path token."""
    loc = _BUNDLE_PREFIX.sub("", location.strip())
    loc = _LINE_SUFFIX.sub("", loc)
    loc = loc.replace("\\", "/").strip().lower()
    return loc.lstrip("./")


def _anchors(location: str) -> tuple[str | None, str | None]:
    """Return (loc-key, base-key) for a source_location, or Nones."""
    loc = _norm_location(location)
    if not loc:
        return None, None
    base = loc.rsplit("/", 1)[-1]
    return loc, base if base != loc else None


@dataclass
class SideView:
    """One finding plus the evidence it cites, flattened for matching."""

    finding: Finding
    evidence: list[Evidence] = field(default_factory=list)
    loc_keys: set[str] = field(default_factory=set)
    base_keys: set[str] = field(default_factory=set)

    @property
    def origins(self) -> list[str]:
        return sorted({e.source for e in self.evidence}) or ["(no evidence)"]


def _view(finding: Finding, evidence_by_id: dict[str, Evidence]) -> SideView:
    ev = [evidence_by_id[eid] for eid in finding.evidence_ids if eid in evidence_by_id]
    loc_keys: set[str] = set()
    base_keys: set[str] = set()
    for e in ev:
        loc, base = _anchors(e.source_location)
        if loc:
            loc_keys.add(loc)
        if base:
            base_keys.add(base)
    return SideView(finding=finding, evidence=ev, loc_keys=loc_keys, base_keys=base_keys)


@dataclass
class CorrelatedPair:
    """One deterministic doctorxsentinel match — both origins preserved."""

    match_strength: str
    matched_keys: list[str]
    doctor_finding_id: str
    doctor_status: str
    doctor_severity: str
    doctor_origins: list[str]
    doctor_confidence: float | None
    sentinel_finding_id: str
    sentinel_status: str
    sentinel_severity: str
    sentinel_origins: list[str]
    sentinel_confidence: float | None


@dataclass
class CrossCorrelationReport:
    """The correlate verb output — a report section, never a verdict."""

    schema: str = "sentinel/doctor-correlation/v1"
    pairs: list[CorrelatedPair] = field(default_factory=list)
    doctor_only: list[str] = field(default_factory=list)
    sentinel_only: list[str] = field(default_factory=list)
    doctor_absent: bool = False
    no_confirmation_upgrade: bool = True
    disclaimer: str = DISCLAIMER
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "pairs": [
                {
                    "match_strength": p.match_strength,
                    "matched_keys": p.matched_keys,
                    "doctor": {
                        "finding_id": p.doctor_finding_id,
                        "status": p.doctor_status,
                        "severity": p.doctor_severity,
                        "origins": p.doctor_origins,
                        "confidence": p.doctor_confidence,
                    },
                    "sentinel": {
                        "finding_id": p.sentinel_finding_id,
                        "status": p.sentinel_status,
                        "severity": p.sentinel_severity,
                        "origins": p.sentinel_origins,
                        "confidence": p.sentinel_confidence,
                    },
                }
                for p in self.pairs
            ],
            "doctor_only": self.doctor_only,
            "sentinel_only": self.sentinel_only,
            "doctor_absent": self.doctor_absent,
            "no_confirmation_upgrade": self.no_confirmation_upgrade,
            "disclaimer": self.disclaimer,
            "limitations": self.limitations,
        }


def _confidence(evidence: list[Evidence]) -> float | None:
    """Best declared confidence across the finding's evidence — verbatim."""
    if not evidence:
        return None
    return max(e.confidence for e in evidence)


def correlate_findings(
    doctor_findings: list[Finding],
    doctor_evidence: list[Evidence],
    sentinel_findings: list[Finding],
    sentinel_evidence: list[Evidence],
) -> CrossCorrelationReport:
    """Match the two finding sets over declared keys; deterministic output.

    Ordering is stable: pairs sorted by (strength rank, doctor id,
    sentinel id) so identical inputs yield byte-identical reports.
    """
    report = CrossCorrelationReport()
    if not doctor_findings:
        report.doctor_absent = True
        report.limitations.append(
            "no doctor findings supplied — sentinel findings reported uncorrelated"
        )
        report.sentinel_only = sorted(f.finding_id for f in sentinel_findings)
        return report

    d_ev = {e.evidence_id: e for e in doctor_evidence}
    s_ev = {e.evidence_id: e for e in sentinel_evidence}
    doctor_views = [_view(f, d_ev) for f in doctor_findings]
    sentinel_views = [_view(f, s_ev) for f in sentinel_findings]

    # Inverted index: loc/base token -> sentinel view indexes.
    loc_index: dict[str, list[int]] = {}
    base_index: dict[str, list[int]] = {}
    for i, sv in enumerate(sentinel_views):
        for key in sv.loc_keys:
            loc_index.setdefault(key, []).append(i)
        for key in sv.base_keys:
            base_index.setdefault(key, []).append(i)

    matched_doctor: set[str] = set()
    matched_sentinel: set[str] = set()
    for dv in doctor_views:
        candidates: dict[int, tuple[str, str]] = {}  # sentinel idx -> (strength, key)
        for key in sorted(dv.loc_keys):
            for i in loc_index.get(key, []):
                same_cat = sentinel_views[i].finding.category == dv.finding.category
                strength = "path+category" if same_cat else "path-only"
                prev = candidates.get(i)
                if prev is None or strength < prev[0]:
                    candidates[i] = (strength, f"loc:{key}")
        for key in sorted(dv.base_keys):
            for i in base_index.get(key, []):
                if i in candidates:
                    continue  # a loc-level match always outranks basename
                if sentinel_views[i].finding.category == dv.finding.category:
                    candidates[i] = ("basename+category", f"base:{key}")
        for i, (strength, key) in sorted(candidates.items()):
            sv = sentinel_views[i]
            report.pairs.append(
                CorrelatedPair(
                    match_strength=strength,
                    matched_keys=[key, f"category:{dv.finding.category.value}"]
                    if strength != "path-only"
                    else [key],
                    doctor_finding_id=dv.finding.finding_id,
                    doctor_status=dv.finding.status.value,
                    doctor_severity=dv.finding.severity.value,
                    doctor_origins=dv.origins,
                    doctor_confidence=_confidence(dv.evidence),
                    sentinel_finding_id=sv.finding.finding_id,
                    sentinel_status=sv.finding.status.value,
                    sentinel_severity=sv.finding.severity.value,
                    sentinel_origins=sv.origins,
                    sentinel_confidence=_confidence(sv.evidence),
                )
            )
            matched_doctor.add(dv.finding.finding_id)
            matched_sentinel.add(sv.finding.finding_id)

    strength_rank = {"path+category": 0, "basename+category": 1, "path-only": 2}
    report.pairs.sort(
        key=lambda p: (
            strength_rank.get(p.match_strength, 9),
            p.doctor_finding_id,
            p.sentinel_finding_id,
        )
    )
    report.doctor_only = sorted(
        f.finding_id for f in doctor_findings if f.finding_id not in matched_doctor
    )
    report.sentinel_only = sorted(
        f.finding_id for f in sentinel_findings if f.finding_id not in matched_sentinel
    )
    if any(p.match_strength == "basename+category" for p in report.pairs):
        report.limitations.append(
            "basename+category matches rely on file names only — "
            "same-named artifacts in different directories collide"
        )
    if any(p.match_strength == "path-only" for p in report.pairs):
        report.limitations.append(
            "path-only matches share an artifact anchor but the producers "
            "classified it under different categories — a signal, not a merge"
        )
    return report
