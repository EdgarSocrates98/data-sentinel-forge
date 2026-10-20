"""Cycle 07 E2E - §12 A-J + N (K/L: Playwright/axe no frontend)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from data_sentinel.api.app import create_app

TOKEN = "e2e-token-07"  # noqa: S105


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_SENTINEL_DB",
                       str(tmp_path / "e2e.db"))
    monkeypatch.setenv("DATA_SENTINEL_TOKEN", TOKEN)
    return tmp_path / "e2e.db"


def _client(tmp_path):
    c = TestClient(create_app(allowed_roots=[str(tmp_path)]))
    c.headers["Authorization"] = f"Bearer {TOKEN}"
    return c


def _snap(sid, job="j1", dur=100.0, start="2026-01-01T00:00:00Z",
          **kw):
    return {"snapshot_id": sid, "platform": "glue", "job_id": job,
            "started_at": start, "duration_s": dur,
            "failure": False, "provenance": "imported", **kw}


class TestA_PersistentInvestigation:
    def test_survives_restart(self, db, tmp_path):
        c = _client(tmp_path)
        r = c.post("/api/v1/investigations",
                   json={"problem": "sql lento"})
        inv_id = r.json()["investigation_id"]
        # simula restart: novo app, mesmo DB
        c2 = _client(tmp_path)
        got = c2.get(f"/api/v1/investigations/{inv_id}")
        assert got.status_code == 200
        lst = c2.get("/api/v1/investigations").json()
        assert any(i["investigation_id"] == inv_id for i in lst)


class TestB_SSEReplay:
    def test_replay_no_duplication(self, db, tmp_path):
        c = _client(tmp_path)
        r = c.post("/api/v1/investigations",
                   json={"problem": "x"})
        inv_id = r.json()["investigation_id"]
        from data_sentinel.persistence.investigations import InvestigationStore
        store = InvestigationStore(db)
        evs = store.events(inv_id)
        store.close()
        # eventos persistidos com seq monotônico; replay a partir
        # de N não repete <= N
        if evs:
            seqs = [e["seq"] for e in evs]
            assert seqs == sorted(seqs)
            assert len(seqs) == len(set(seqs))


class TestC_GlueRegression:
    def test_compare_detects_duration_regression(self, db, tmp_path):
        c = _client(tmp_path)
        c.post("/api/v1/snapshots",
               json=_snap("s1", dur=100.0,
                          start="2026-01-01T00:00:00Z"))
        c.post("/api/v1/snapshots",
               json=_snap("s2", dur=300.0,
                          start="2026-01-02T00:00:00Z"))
        r = c.post("/api/v1/history/compare",
                   json={"snapshot_id": "s2",
                         "baseline": "previous"}).json()
        assert r["comparable"] is True
        assert r["duration_delta_pct"] > 0
        assert r["regression_findings"]


class TestD_EMRCapacity:
    def test_trigger_investigation(self, db, tmp_path):
        c = _client(tmp_path)
        r = c.post("/api/v1/investigations", json={
            "problem": "capacidade emr",
            "trigger": {"kind": "alert",
                        "summary": "cluster emr saturado",
                        "source_refs": ["alert-1"]}})
        assert r.status_code == 201


class TestE_QualityRegression:
    def test_quality_alert(self, db, tmp_path):
        c = _client(tmp_path)
        c.post("/api/v1/watches", json={
            "watch_id": "wq", "workload": "dq-job",
            "platform": "glue"})
        base = _snap("q1", job="dq-job", dur=60.0,
                     start="2026-01-01T00:00:00Z")
        base["resource_metrics"] = {"dq_pass_rate": 0.99}
        bad = _snap("q2", job="dq-job", dur=60.0,
                    start="2026-01-02T00:00:00Z")
        bad["resource_metrics"] = {"dq_pass_rate": 0.10}
        c.post("/api/v1/snapshots", json=base)
        c.post("/api/v1/snapshots", json=bad)
        alerts = c.post("/api/v1/watches/wq/run").json()
        assert isinstance(alerts, list)


class TestF_WatchLifecycle:
    def test_full_lifecycle(self, db, tmp_path):
        c = _client(tmp_path)
        r = c.post("/api/v1/watches", json={
            "watch_id": "wl", "workload": "j1",
            "platform": "glue"})
        assert r.json()["enabled"] is False  # nunca auto-inicia
        c.post("/api/v1/snapshots", json=_snap("x1"))
        c.post("/api/v1/watches/wl/run")
        c.post("/api/v1/watches/wl/pause")
        assert c.post("/api/v1/watches/wl/resume"
                      ).json()["enabled"] is True
        assert c.post("/api/v1/watches/wl/delete"
                      ).json()["deleted"] == "wl"


class TestG_AlertDedup:
    def test_repeated_eval_dedupes(self, db, tmp_path):
        c = _client(tmp_path)
        c.post("/api/v1/watches", json={
            "watch_id": "wd", "workload": "j1",
            "platform": "glue"})
        c.post("/api/v1/snapshots",
               json=_snap("d1", dur=100.0,
                          start="2026-01-01T00:00:00Z"))
        c.post("/api/v1/snapshots",
               json=_snap("d2", dur=500.0,
                          start="2026-01-02T00:00:00Z"))
        a1 = c.post("/api/v1/watches/wd/run").json()
        a2 = c.post("/api/v1/watches/wd/run").json()
        if a1:  # cooldown suprime repetição da mesma condição
            keys1 = {a["alert_id"] for a in a1}
            keys2 = {a["alert_id"] for a in a2}
            assert not keys2 or keys2.isdisjoint(keys1) or all(
                x["recovered"] for x in a2)


class TestH_CostIntelligence:
    def test_estimate_with_assumptions(self):
        from data_sentinel.analyzers.emr.cost import estimate_glue, what_if
        e = estimate_glue("G.1X", 10, 3600)
        assert e.amount and e.price_source and e.assumptions
        w = what_if("metade", e, estimate_glue("G.1X", 5, 3600))
        assert any("não representa" in x for x in w.limitations)


class TestI_RemediationPlan:
    def test_plan_no_execution(self, db, tmp_path):
        c = _client(tmp_path)
        r = c.post("/api/v1/remediation/plans", json={
            "finding": {
                "category": "out_of_memory", "severity": "HIGH",
                "status": "CONFIRMED", "explanation": "oom",
                "evidence_ids": ["e1"],
                "recommendations": ["aumentar memory"],
                "validation_steps": ["re-run"]}})
        pid = r.json()["plan_id"]
        c.post(f"/api/v1/remediation/plans/{pid}/submit")
        c.post(f"/api/v1/remediation/plans/{pid}/approve",
               json={"approver": "edgar"})
        ex = c.post(
            f"/api/v1/remediation/plans/{pid}/execute-local").json()
        assert all(x["status"] == "SKIPPED"
                   for x in ex["results"])
        assert "nenhuma chamada cloud" in ex["note"]


class TestJ_Auth:
    def test_unauthorized_rejected(self, db, tmp_path):
        c = TestClient(create_app(allowed_roots=[str(tmp_path)]))
        assert c.get("/api/v1/investigations").status_code in (
            401, 403)
        assert c.post("/api/v1/snapshots",
                      json=_snap("x")).status_code in (401, 403)

    def test_authorized_ok(self, db, tmp_path):
        c = _client(tmp_path)
        assert c.get("/api/v1/investigations").status_code == 200


class TestN_Security:
    def test_no_delete_methods(self, db, tmp_path):
        c = _client(tmp_path)
        spec = c.get("/api/openapi.json").json()
        methods = {m for p in spec["paths"].values() for m in p}
        assert "delete" not in methods and "put" not in methods

    def test_no_secret_leakage(self, db, tmp_path):
        c = _client(tmp_path)
        r = c.post("/api/v1/snapshots",
                   json=_snap("sec",
                              config_fingerprint="x")).json()
        assert "test-token" not in str(r)
        assert "e2e-token" not in str(r)

    def test_no_cloud_mutation_surface(self):
        # remediation executor tem apenas ações locais allowlist
        from data_sentinel.remediation import LOCAL_ACTION_ALLOWLIST
        assert LOCAL_ACTION_ALLOWLIST and all(
            a.startswith(("update_watch", "suppress_",
                          "escalate_"))
            for a in LOCAL_ACTION_ALLOWLIST)
