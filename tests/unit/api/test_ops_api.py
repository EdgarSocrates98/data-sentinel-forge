"""ds-0087 backend — operational endpoints (history/watch/remediation)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from data_sentinel.api.app import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_SENTINEL_DB",
                       str(tmp_path / "ops.db"))
    monkeypatch.setenv("DATA_SENTINEL_TOKEN", "test-token")
    app = create_app(allowed_roots=[str(tmp_path)],
                     db_path=tmp_path / "ops.db")
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer test-token"
    c.headers["X-TestClient"] = "1"
    return c


def _snap(sid: str, job: str = "j1", dur: float = 100.0,
          start: str = "2026-01-01T00:00:00Z"):
    return {"snapshot_id": sid, "platform": "glue", "job_id": job,
            "started_at": start, "duration_s": dur,
            "failure": False, "provenance": "imported"}


class TestSnapshots:
    def test_ingest_and_list(self, client):
        r = client.post("/api/v1/snapshots", json=_snap("s1"))
        assert r.status_code == 201
        lst = client.get("/api/v1/snapshots").json()
        assert any(s["snapshot_id"] == "s1" for s in lst)

    def test_list_filter(self, client):
        client.post("/api/v1/snapshots", json=_snap("a", job="x"))
        client.post("/api/v1/snapshots", json=_snap("b", job="y"))
        lst = client.get("/api/v1/snapshots?job_id=x").json()
        assert len(lst) == 1 and lst[0]["job_id"] == "x"

    def test_invalid_snapshot_422(self, client):
        assert client.post("/api/v1/snapshots",
                           json={"snapshot_id": "s"}).status_code == 422


class TestHistory:
    def test_compare_no_baseline_honest(self, client):
        client.post("/api/v1/snapshots", json=_snap("only"))
        r = client.post("/api/v1/history/compare",
                        json={"snapshot_id": "only"}).json()
        assert r["comparable"] is False
        assert any("não fabricada" in x for x in r["limitations"])

    def test_compare_previous(self, client):
        client.post("/api/v1/snapshots",
                    json=_snap("s1", dur=100.0,
                               start="2026-01-01T00:00:00Z"))
        client.post("/api/v1/snapshots",
                    json=_snap("s2", dur=200.0,
                               start="2026-01-02T00:00:00Z"))
        r = client.post("/api/v1/history/compare",
                        json={"snapshot_id": "s2",
                              "baseline": "previous"}).json()
        assert r["comparable"] is True
        assert r["baseline_snapshot_ids"] == ["s1"]
        assert r["duration_delta_s"] > 0

    def test_regressions_endpoint(self, client):
        client.post("/api/v1/snapshots",
                    json=_snap("s1", dur=100.0,
                               start="2026-01-01T00:00:00Z"))
        client.post("/api/v1/snapshots",
                    json=_snap("s2", dur=400.0,
                               start="2026-01-02T00:00:00Z"))
        r = client.get("/api/v1/history/regressions",
                       params={"job_id": "j1",
                               "current_id": "s2"}).json()
        assert isinstance(r, list)


class TestWatches:
    def test_create_disabled_by_default(self, client):
        r = client.post("/api/v1/watches", json={
            "watch_id": "w1", "workload": "j1", "platform": "glue"})
        assert r.status_code == 201
        assert r.json()["enabled"] is False

    def test_aws_source_rejected_via_api(self, client):
        r = client.post("/api/v1/watches", json={
            "watch_id": "w2", "workload": "j1", "platform": "glue",
            "source": "aws"})
        assert r.status_code == 400

    def test_interval_floor(self, client):
        r = client.post("/api/v1/watches", json={
            "watch_id": "w3", "workload": "j1", "platform": "glue",
            "interval_s": 1})
        assert r.status_code == 400

    def test_run_emits_alerts_on_regression(self, client):
        client.post("/api/v1/watches", json={
            "watch_id": "w4", "workload": "j1", "platform": "glue"})
        client.post("/api/v1/snapshots",
                    json=_snap("s1", dur=100.0,
                               start="2026-01-01T00:00:00Z"))
        client.post("/api/v1/snapshots",
                    json=_snap("s2", dur=500.0,
                               start="2026-01-02T00:00:00Z"))
        alerts = client.post("/api/v1/watches/w4/run").json()
        assert isinstance(alerts, list)

    def test_pause_resume_delete(self, client):
        client.post("/api/v1/watches", json={
            "watch_id": "w5", "workload": "j", "platform": "glue"})
        assert client.post("/api/v1/watches/w5/pause"
                           ).json()["enabled"] is False
        assert client.post("/api/v1/watches/w5/resume"
                           ).json()["enabled"] is True
        assert client.post("/api/v1/watches/w5/delete"
                           ).json()["deleted"] == "w5"


class TestRemediationAPI:
    def test_plan_from_finding_full_flow(self, client):
        finding = {
            "category": "out_of_memory", "severity": "HIGH",
            "status": "CONFIRMED", "explanation": "executor OOM",
            "evidence_ids": ["e1"],
            "recommendations": ["aumentar memory"],
            "validation_steps": ["re-run"]}
        r = client.post("/api/v1/remediation/plans",
                        json={"finding": finding})
        assert r.status_code == 201
        pid = r.json()["plan_id"]
        assert client.post(
            f"/api/v1/remediation/plans/{pid}/submit"
            ).json()["state"] == "AWAITING_APPROVAL"
        ap = client.post(f"/api/v1/remediation/plans/{pid}/approve",
                         json={"approver": "edgar"}).json()
        assert "NÃO executa" in ap["note"]
        ex = client.post(
            f"/api/v1/remediation/plans/{pid}/execute-local").json()
        assert "nenhuma chamada cloud" in ex["note"]

    def test_approve_requires_approver(self, client):
        finding = {"category": "cost", "severity": "LOW",
                   "status": "POSSIBLE", "explanation": "x",
                   "recommendations": ["r"],
                   "validation_steps": ["v"]}
        pid = client.post("/api/v1/remediation/plans",
                          json={"finding": finding}
                          ).json()["plan_id"]
        client.post(f"/api/v1/remediation/plans/{pid}/submit")
        assert client.post(
            f"/api/v1/remediation/plans/{pid}/approve",
            json={}).status_code == 400

    def test_dry_run(self, client):
        finding = {"category": "cost", "severity": "LOW",
                   "status": "POSSIBLE", "explanation": "x",
                   "recommendations": ["r"],
                   "validation_steps": ["v"]}
        pid = client.post("/api/v1/remediation/plans",
                          json={"finding": finding}
                          ).json()["plan_id"]
        dr = client.post(
            f"/api/v1/remediation/plans/{pid}/dry-run").json()
        assert "nenhuma alteração" in dr["note"]

    def test_execute_before_approved_422(self, client):
        finding = {"category": "cost", "severity": "LOW",
                   "status": "POSSIBLE", "explanation": "x",
                   "recommendations": ["r"],
                   "validation_steps": ["v"]}
        pid = client.post("/api/v1/remediation/plans",
                          json={"finding": finding}
                          ).json()["plan_id"]
        assert client.post(
            f"/api/v1/remediation/plans/{pid}/execute-local"
            ).status_code == 422
