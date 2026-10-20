"""ds-0086 / §7 — supervised remediation planning."""
from __future__ import annotations

import pytest

from data_sentinel.core.contracts.entities import Finding
from data_sentinel.core.contracts.enums import FindingCategory, FindingStatus, Severity
from data_sentinel.remediation import (
    LOCAL_ACTION_ALLOWLIST,
    PlanState,
    ProposedChange,
    approve,
    dry_run,
    execute_local,
    export_plan,
    plan_for_finding,
    reject,
    submit_for_approval,
    validate_plan,
)


def _finding(**kw):
    return Finding(
        category=kw.get("category", FindingCategory.OUT_OF_MEMORY),
        severity=kw.get("severity", Severity.HIGH),
        status=kw.get("status", FindingStatus.CONFIRMED),
        explanation=kw.get("explanation", "executor OOM"),
        evidence_ids=kw.get("evidence_ids", ["ev-1"]),
        recommendations=kw.get("recommendations",
                               ["aumentar spark.executor.memory"]),
        validation_steps=kw.get("validation_steps", ["reexecutar"]))


def _approved():
    p = submit_for_approval(plan_for_finding(_finding()))
    return approve(p, "edgar")


class TestWorkflow:
    def test_starts_draft(self):
        assert plan_for_finding(_finding()).state == PlanState.DRAFT

    def test_full_path(self):
        p = _approved()
        assert p.state == PlanState.APPROVED
        states = [h["to"] for h in p.state_history]
        assert states[:3] == ["DRAFT", "VALIDATED",
                              "AWAITING_APPROVAL"]

    def test_invalid_transition(self):
        p = plan_for_finding(_finding())
        with pytest.raises(ValueError, match="transição inválida"):
            approve(p, "edgar")

    def test_reject(self):
        p = reject(plan_for_finding(_finding()), "sem evidência")
        assert p.state == PlanState.REJECTED

    def test_incomplete_plan_blocked(self):
        p = plan_for_finding(_finding())
        p.validation_procedure = []
        p.rollback_proposal = None
        with pytest.raises(ValueError, match="plano incompleto"):
            submit_for_approval(p)

    def test_anonymous_approval_rejected(self):
        p = submit_for_approval(plan_for_finding(_finding()))
        with pytest.raises(ValueError, match="approver"):
            approve(p, "")


class TestDryRun:
    def test_structured_preview(self):
        p = plan_for_finding(_finding())
        dr = dry_run(p)
        assert dr["would_change"] and "nenhuma alteração" in dr["note"]

    def test_dry_run_executes_nothing(self):
        p = plan_for_finding(_finding())
        before = p.state
        dry_run(p)
        assert p.state == before


class TestExecuteLocal:
    def test_requires_approved(self):
        p = plan_for_finding(_finding())
        with pytest.raises(ValueError, match="APPROVED"):
            execute_local(p)

    def test_non_local_action_skipped(self):
        p = _approved()
        res = execute_local(p)
        assert all(r["status"] == "SKIPPED" for r in res["results"])
        assert "nenhuma chamada cloud" in res["note"]

    def test_allowlisted_action_applies(self):
        p = _approved()
        p.proposed_changes = [ProposedChange(
            target="watch:w1", change="threshold",
            params={"k": 1.5}, local_action="update_watch_threshold")]
        calls = []
        res = execute_local(p, apply_fn={
            "update_watch_threshold":
                lambda params: calls.append(params) or "ok"})
        assert res["results"][0]["status"] == "APPLIED"
        assert calls == [{"k": 1.5}]

    def test_off_allowlist_blocked(self):
        p = _approved()
        p.proposed_changes = [ProposedChange(
            target="s3", change="delete",
            params={}, local_action="delete_s3_bucket")]
        res = execute_local(p)
        assert res["results"][0]["status"] == "BLOCKED"

    def test_allowlist_is_local_only(self):
        banned = {"delete", "drop", "glue_", "s3_", "emr_"}
        for a in LOCAL_ACTION_ALLOWLIST:
            assert not any(b in a for b in banned)


class TestExport:
    def test_interop_envelope(self):
        p = _approved()
        e = export_plan(p)
        assert e["contract"] == "forge-contracts/1"
        assert e["kind"] == "sentinel.remediation_plan"
        assert e["limitations"]

    def test_validate_checklist(self):
        assert validate_plan(plan_for_finding(_finding())) == []
