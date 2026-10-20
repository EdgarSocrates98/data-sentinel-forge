"""Root-cause engine (§8.1-§8.2) — deterministic hypothesis ranking.

Clusters findings by category → Hypothesis objects (real contract:
``open|supported|refuted|dropped``, ``causal_label`` enforces the
correlation-is-not-causation rule). Score comes from evidence count,
status and severity; ranking is deterministic.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from data_sentinel.core.contracts.agent import Hypothesis
from data_sentinel.core.contracts.entities import Finding
from data_sentinel.core.contracts.enums import FindingStatus, Severity

_SEV_W = {Severity.INFO: 0.5, Severity.LOW: 0.6, Severity.MEDIUM: 0.8,
          Severity.HIGH: 1.0, Severity.CRITICAL: 1.0}
_STATUS_W = {FindingStatus.CONFIRMED: 1.0, FindingStatus.PROBABLE: 0.8,
             FindingStatus.POSSIBLE: 0.5, FindingStatus.UNKNOWN: 0.2}
_CONF = {FindingStatus.CONFIRMED: "CONFIRMED",
         FindingStatus.PROBABLE: "PROBABLE",
         FindingStatus.POSSIBLE: "POSSIBLE",
         FindingStatus.UNKNOWN: "UNKNOWN"}


@dataclass
class RCAResult:
    hypotheses: list[Hypothesis] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    primary: Hypothesis | None = None
    limitations: list[str] = field(default_factory=list)


class RootCauseEngine:
    """Cluster findings → scored hypotheses → root-cause result."""

    def analyze(self, findings: list[Finding]) -> RCAResult:
        if not findings:
            return RCAResult(limitations=[
                "nenhum finding fornecido — RCA não inventa causa"])
        clusters: dict[str, list[Finding]] = defaultdict(list)
        for f in findings:
            clusters[f.category.value].append(f)

        res = RCAResult()
        for cat, group in sorted(clusters.items()):
            ev = sorted({e for f in group for e in f.evidence_ids})
            n_conf = sum(f.status == FindingStatus.CONFIRMED
                         for f in group)
            n_unk = sum(f.status == FindingStatus.UNKNOWN
                        for f in group)
            score = min(1.0, sum(
                _SEV_W[f.severity] * _STATUS_W[f.status]
                for f in group) / len(group))
            best_status = max(
                (f.status for f in group),
                key=lambda s: _STATUS_W[s])
            alts = [f.explanation[:120] for f in group
                    if f.status == FindingStatus.UNKNOWN]
            if n_unk:
                alts.insert(0,
                            f"{n_unk} finding(s) UNKNOWN neste cluster")
            h = Hypothesis(
                hypothesis_id=f"rca:{cat}",
                statement=(
                    f"causa-raiz provável em '{cat}': {len(group)} "
                    f"finding(s), {n_conf} confirmado(s)"),
                status=("supported" if ev and n_conf else "open"),
                supporting_evidence=ev,
                confidence=_CONF[best_status],
                alternatives=alts,
                causal_label="suspected_cause",
            )
            res.hypotheses.append(h)
            res.scores[h.hypothesis_id] = round(score, 3)

        res.hypotheses.sort(
            key=lambda h: (-res.scores[h.hypothesis_id], h.statement))
        res.primary = res.hypotheses[0] if res.hypotheses else None
        if not res.primary or res.scores.get(
                res.primary.hypothesis_id, 0) < 0.5:
            res.limitations.append(
                "confiança baixa em todos os clusters — mais evidência "
                "pode mudar a conclusão")
        return res
