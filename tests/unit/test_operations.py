"""ds-0088 / §9 — operational triggers, hypothesis labels, memory."""
from __future__ import annotations

from data_sentinel.agents.memory import recall, remember, summarize
from data_sentinel.agents.operations import (
    CauseLabel,
    evaluate_hypothesis,
    trigger_from_alert,
    trigger_from_regression,
    trigger_investigation,
)
from data_sentinel.core.contracts.snapshot import ExecutionSnapshot


def _snap(sid, dur=100.0, start="2026-01-01T00:00:00Z", **kw):
    kw.setdefault("failure", False)
    return ExecutionSnapshot(
        snapshot_id=sid, platform="glue", job_id="j1",
        started_at=start, duration_s=dur,
        provenance="imported", **kw)


class TestTriggers:
    def test_trigger_investigation_records_context(self):
        t = trigger_from_alert({"alert_id": "a1",
                                "message": "job j1 falhou",
                                "watch_id": "w1",
                                "kind": "job_failure"})
        rep = trigger_investigation(t)
        trig = rep.context["operational_trigger"]
        assert trig["kind"] == "alert"
        assert any("sem artefatos" in x
                   for x in rep.limitations)

    def test_regression_trigger_summary(self):
        t = trigger_from_regression(
            "j1", [{"metric": "duration_s", "rationale": "x"}])
        assert "j1" in t.summary and "duration_s" in t.summary

    def test_sanitizes_problem(self):
        t = trigger_from_alert({"alert_id": "a",
                                "message": "x" * 10_000})
        assert len(t.to_problem()) <= 2_100


class TestHypothesisLabels:
    def test_regression_without_changes(self):
        h = evaluate_hypothesis(
            [_snap("a", 100.0)],
            _snap("b", 500.0, start="2026-01-02T00:00:00Z"))
        assert h.label == CauseLabel.OBSERVED_REGRESSION
        assert h.supporting

    def test_regression_with_associated_change(self):
        hist = [_snap("a", 100.0, config_fingerprint="f1")]
        cur = _snap("b", 500.0, start="2026-01-02T00:00:00Z",
                    config_fingerprint="f2")
        h = evaluate_hypothesis(hist, cur)
        assert h.label == CauseLabel.ASSOCIATED_EVENT
        assert any("causalidade" in x for x in h.limitations)

    def test_failure_without_metrics(self):
        h = evaluate_hypothesis(
            [_snap("a", 100.0)],
            _snap("b", None, start="2026-01-02T00:00:00Z",
                  failure=True))
        assert h.label == CauseLabel.OBSERVED_REGRESSION
        assert "falha" in h.statement

    def test_no_regression_unknown(self):
        h = evaluate_hypothesis([_snap("a", 100.0)],
                                _snap("b", 105.0,
                                      start="2026-01-02T00:00:00Z"))
        assert h.label == CauseLabel.UNKNOWN

    def test_never_confirmed(self):
        labels = {h.label for h in [
            evaluate_hypothesis([_snap("a")],
                                _snap("b", 900.0,
                                      start="2026-01-02T00:00:00Z"))]}
        assert not any("confirm" in str(x).lower() for x in labels)


class TestMemory:
    def test_roundtrip(self, tmp_path):
        from data_sentinel.core.contracts.agent import InvestigationReport
        rep = InvestigationReport(
            report_id="r1", investigation_id="i1",
            problem="glue job slow password=hunter22extra")
        s = remember(rep, tmp_path / "m.db")
        assert s.problem_hash and "hunter22extra" not in s.problem_excerpt
        rows = recall(tmp_path / "m.db")
        assert rows and rows[0]["report_id"] == "r1"

    def test_summary_fields(self):
        from data_sentinel.core.contracts.agent import InvestigationReport
        from data_sentinel.core.contracts.entities import Finding
        from data_sentinel.core.contracts.enums import FindingCategory, FindingStatus, Severity
        rep = InvestigationReport(
            report_id="r2", investigation_id="i2", problem="p")
        rep.findings = [Finding(
            category=FindingCategory.OUT_OF_MEMORY,
            severity=Severity.HIGH,
            status=FindingStatus.CONFIRMED, explanation="x",
            evidence_ids=["e"])]
        s = summarize(rep)
        assert s.findings_count == 1
        assert "out_of_memory" in s.categories

    def test_no_full_problem_persisted(self, tmp_path):
        from data_sentinel.core.contracts.agent import InvestigationReport
        long_problem = "detalhes " * 500
        rep = InvestigationReport(
            report_id="r3", investigation_id="i3",
            problem=long_problem)
        s = remember(rep, tmp_path / "m2.db")
        assert len(s.problem_excerpt) <= 120
        assert s.problem_hash != long_problem
