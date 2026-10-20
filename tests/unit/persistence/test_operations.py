"""ds-0091 / §2.1 — operational persistence: versioned schema."""
from __future__ import annotations

import sqlite3
import threading

import pytest

from data_sentinel.core.contracts.entities import Finding
from data_sentinel.core.contracts.enums import FindingCategory, FindingStatus, Severity
from data_sentinel.core.contracts.snapshot import ExecutionSnapshot
from data_sentinel.persistence.operations import OpsStore
from data_sentinel.remediation.plans import (
    PlanState,
    approve,
    plan_for_finding,
    submit_for_approval,
)
from data_sentinel.watch.engine import Alert, WatchDefinition


def _snap(sid: str, job: str = "j1", dur: float = 10.0,
          start: str = "2026-01-01T00:00:00Z"):
    return ExecutionSnapshot(
        snapshot_id=sid, platform="glue", job_id=job,
        started_at=start, duration_s=dur, failure=False,
        provenance="test")


def _watch(wid: str = "w1", enabled: bool = False):
    return WatchDefinition(watch_id=wid, workload="j1",
                           platform="glue", source="local",
                           enabled=enabled)


def _plan(state: PlanState = PlanState.DRAFT):
    f = Finding(category=FindingCategory.OUT_OF_MEMORY,
                severity=Severity.HIGH, status=FindingStatus.CONFIRMED,
                explanation="oom", evidence_ids=["e"],
                recommendations=["r"], validation_steps=["v"])
    p = plan_for_finding(f)
    if state == PlanState.APPROVED:
        p = submit_for_approval(p)
        p = approve(p, "edgar")
    return p


class TestSnapshots:
    def test_roundtrip(self, tmp_path):
        s = OpsStore(tmp_path / "o.db")
        s.save_snapshot(_snap("s1"))
        assert s.get_snapshot("s1").duration_s == 10.0
        s.close()

    def test_survives_restart(self, tmp_path):
        db = tmp_path / "o.db"
        OpsStore(db).save_snapshot(_snap("s1"))
        s2 = OpsStore(db)
        assert s2.get_snapshot("s1") is not None
        assert s2.list_snapshots(job_id="j1")

    def test_list_filters_sorted(self, tmp_path):
        s = OpsStore(tmp_path / "o.db")
        s.save_snapshot(_snap("b", start="2026-01-02T00:00:00Z"))
        s.save_snapshot(_snap("a", start="2026-01-01T00:00:00Z"))
        s.save_snapshot(_snap("c", job="j2"))
        lst = s.list_snapshots(job_id="j1")
        assert [x.snapshot_id for x in lst] == ["a", "b"]
        assert len(s.list_snapshots(platform="glue")) == 3


class TestWatches:
    def test_disabled_state_persisted(self, tmp_path):
        db = tmp_path / "o.db"
        OpsStore(db).save_watch(_watch("w1", enabled=False))
        w = OpsStore(db).get_watch("w1")
        assert w.enabled is False  # restart não auto-habilita

    def test_enabled_persisted_not_autostarted(self, tmp_path):
        db = tmp_path / "o.db"
        OpsStore(db).save_watch(_watch("w2", enabled=True))
        w = OpsStore(db).get_watch("w2")
        assert w.enabled is True  # enabled persistido; polling é
        # manual — não há loop automático na API por design

    def test_delete(self, tmp_path):
        s = OpsStore(tmp_path / "o.db")
        s.save_watch(_watch())
        assert s.delete_watch("w1") is True
        assert s.get_watch("w1") is None


class TestAlerts:
    def test_execution_and_alerts(self, tmp_path):
        s = OpsStore(tmp_path / "o.db")
        a = Alert(alert_id="a1", watch_id="w1", kind="job_failure",
                  severity="HIGH", message="falhou", ts=1.0,
                  dedup_key="w1:failure")
        s.save_watch_execution("w1", [a])
        assert s.list_alerts()[0]["kind"] == "job_failure"
        assert s.list_watch_executions("w1")[0]["result"] == "ok"


class TestPlans:
    def test_state_persists(self, tmp_path):
        db = tmp_path / "o.db"
        p = _plan(PlanState.APPROVED)
        OpsStore(db).save_plan(p)
        got = OpsStore(db).get_plan(p.plan_id)
        assert got.state == PlanState.APPROVED
        assert got.state_history

    def test_approval_records(self, tmp_path):
        s = OpsStore(tmp_path / "o.db")
        s.save_approval("p1", "edgar", "APPROVED", "ok")
        s.save_approval("p1", "edgar", "REJECTED", "nao")
        recs = s.list_approvals("p1")
        assert len(recs) == 2 and recs[0]["decision"] == "APPROVED"


class TestAuditAndLinks:
    def test_audit_trail(self, tmp_path):
        s = OpsStore(tmp_path / "o.db")
        s.audit("api", "remediation.approve", {"plan_id": "p"})
        rows = s.list_audit()
        assert rows[0]["action"] == "remediation.approve"
        assert rows[0]["detail"]["plan_id"] == "p"

    def test_links_dedup(self, tmp_path):
        s = OpsStore(tmp_path / "o.db")
        s.link("inv-1", "plan", "p1")
        s.link("inv-1", "plan", "p1")  # UNIQUE — sem duplicar
        assert len(s.links_for("inv-1")) == 1


class TestOps:
    def test_concurrent_writes(self, tmp_path):
        db = tmp_path / "o.db"
        s = OpsStore(db)

        def work(n: int) -> None:
            st = OpsStore(db)
            for i in range(10):
                st.save_snapshot(_snap(f"t{n}-{i}"))
            st.close()
        threads = [threading.Thread(target=work, args=(n,))
                   for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(s.list_snapshots()) == 40
        s.close()

    def test_retention(self, tmp_path):
        from datetime import UTC, datetime, timedelta
        s = OpsStore(tmp_path / "o.db")
        now = datetime.now(UTC)
        s.save_snapshot(_snap(
            "old", start=(now - timedelta(days=30)).isoformat()))
        s.save_snapshot(_snap(
            "new", start=now.isoformat()))
        removed = s.prune(
            snapshots_older_than_s=86400)
        assert removed["snapshots"] == 1
        assert s.get_snapshot("new") is not None

    def test_backup_restore(self, tmp_path):
        db = tmp_path / "o.db"
        s = OpsStore(db)
        s.save_snapshot(_snap("s1"))
        backup = tmp_path / "backup.db"
        dst = sqlite3.connect(backup)
        s._conn.backup(dst)
        dst.close()
        s.close()
        restored = OpsStore(backup)
        assert restored.get_snapshot("s1") is not None

    def test_versioned_migration(self, tmp_path):
        db = tmp_path / "o.db"
        OpsStore(db).close()
        v = sqlite3.connect(db).execute(
            "PRAGMA user_version").fetchone()[0]
        assert v == 1
        # reabrir é idempotente
        OpsStore(db).close()
        assert sqlite3.connect(db).execute(
            "PRAGMA user_version").fetchone()[0] == 1

    def test_newer_schema_refused(self, tmp_path):
        db = tmp_path / "o.db"
        OpsStore(db).close()
        con = sqlite3.connect(db)
        con.execute("PRAGMA user_version=999")
        con.close()
        with pytest.raises(RuntimeError, match="mais novo"):
            OpsStore(db)

    def test_corrupted_row_does_not_crash_list(self, tmp_path):
        db = tmp_path / "o.db"
        s = OpsStore(db)
        s.save_snapshot(_snap("ok"))
        s._conn.execute(
            "INSERT INTO snapshots (snapshot_id, platform,"
            " payload_json, created_ts) VALUES ('bad','x','{no',0)")
        s._conn.commit()
        import pydantic
        with pytest.raises((sqlite3.DatabaseError, pydantic.ValidationError)):
            s.list_snapshots()  # corrupção é erro explícito, não skip
        assert s.get_snapshot("ok") is not None
        s.close()
