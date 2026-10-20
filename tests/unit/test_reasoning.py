"""Reasoning tests (ds-0056)."""

from data_sentinel.core.contracts.entities import Finding
from data_sentinel.core.contracts.enums import FindingCategory, FindingStatus, Severity
from data_sentinel.reasoning import EvidenceValidator, RootCauseEngine


def _f(cat: FindingCategory, status: FindingStatus,
       sev: Severity = Severity.HIGH,
       ev: list[str] | None = None) -> Finding:
    return Finding(category=cat, severity=sev, status=status,
                   explanation=f"achado {cat.value}",
                   evidence_ids=["ev-1"] if ev is None else ev)


def test_validator_flags_missing_evidence() -> None:
    bad = _f(FindingCategory.OUT_OF_MEMORY, FindingStatus.CONFIRMED,
             ev=[])
    rep = EvidenceValidator().validate([bad])
    assert not rep.ok
    assert "evidence" in rep.issues[0].issue


def test_validator_unknown_needs_alternatives() -> None:
    bad = _f(FindingCategory.UNKNOWN, FindingStatus.UNKNOWN, ev=[])
    rep = EvidenceValidator().validate([bad])
    assert not rep.ok
    bad.alternatives = ["camadas IAM não avaliadas"]
    assert EvidenceValidator().validate([bad]).ok


def test_validator_duplicate_claim() -> None:
    f1 = _f(FindingCategory.DATA_SKEW, FindingStatus.PROBABLE)
    f2 = _f(FindingCategory.DATA_SKEW, FindingStatus.PROBABLE)
    rep = EvidenceValidator().validate([f1, f2])
    assert any("duplicata" in i.issue for i in rep.issues)


def test_rca_ranks_confirmed_first() -> None:
    fs = [
        _f(FindingCategory.PERMISSIONS, FindingStatus.POSSIBLE,
           Severity.LOW),
        _f(FindingCategory.OUT_OF_MEMORY, FindingStatus.CONFIRMED,
           Severity.CRITICAL),
    ]
    r = RootCauseEngine().analyze(fs)
    assert r.primary is not None
    assert "out_of_memory" in r.primary.hypothesis_id
    assert r.primary.status == "supported"
    assert r.primary.causal_label == "suspected_cause"


def test_rca_empty_is_honest() -> None:
    r = RootCauseEngine().analyze([])
    assert not r.hypotheses
    assert "não inventa" in r.limitations[0]


def test_rca_unknown_cluster_keeps_unknowns() -> None:
    f = _f(FindingCategory.NETWORK_IO, FindingStatus.UNKNOWN, ev=[])
    f.alternatives = ["sem logs de rede"]
    r = RootCauseEngine().analyze([f])
    assert r.hypotheses[0].confidence == "UNKNOWN"
    assert r.hypotheses[0].alternatives
