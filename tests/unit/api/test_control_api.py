"""Tests for the Control Center API (ds-0071)."""

from __future__ import annotations

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from data_sentinel.api import create_app  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app(allowed_roots=[str(FIXTURES), str(tmp_path)])
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {app.state.auth.token}"
    return c


def test_health(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_capabilities_lists_emr(client: TestClient) -> None:
    r = client.get("/api/v1/capabilities")
    ids = [c["capability_id"] for c in r.json()]
    assert "sentinel.emr.ec2" in ids


def test_tools_manifest_truthful(client: TestClient) -> None:
    r = client.get("/api/v1/tools")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert "sentinel.spark.analyze_plan" in names
    for t in r.json():
        assert "inputSchema" in t and "description" in t


def test_agents_registry(client: TestClient) -> None:
    r = client.get("/api/v1/agents")
    assert len(r.json()) == 18


def test_analyze_unknown_404(client: TestClient) -> None:
    r = client.post("/api/v1/analyze/nope.x", json={"file": "nonexistent/x"})
    assert r.status_code == 404


def test_analyze_path_traversal_blocked(client: TestClient) -> None:
    r = client.post("/api/v1/analyze/spark.analyze_plan",
                    json={"file": "/etc/passwd"})
    assert r.status_code == 403


def test_analyze_real_sql_fixture(client: TestClient) -> None:
    sql = FIXTURES / "sql" / "cycle2" / "cast_keys.sql"
    r = client.post("/api/v1/analyze/sql.analyze",
                    json={"file": str(sql)})
    assert r.status_code == 200
    assert "findings" in r.json()


def test_investigation_lifecycle(client: TestClient) -> None:
    r = client.post("/api/v1/investigations", json={
        "problem": "Glue job failing with OOM", "files": {}})
    assert r.status_code == 201
    inv_id = r.json()["investigation_id"]
    # poll until complete
    for _ in range(50):
        g = client.get(f"/api/v1/investigations/{inv_id}")
        if g.json().get("status") != "running":
            break
    rep = client.get(f"/api/v1/investigations/{inv_id}").json()
    assert "findings" in rep
    assert rep["investigation_id"] == inv_id


def test_investigation_rejects_bad_file_type(
        client: TestClient, tmp_path: Path) -> None:
    exe = tmp_path / "evil.exe"
    exe.write_bytes(b"MZ")
    r = client.post("/api/v1/investigations", json={
        "problem": "x", "files": {"sentinel.sql.analyze": str(exe)}})
    assert r.status_code == 400


def test_openapi_available(client: TestClient) -> None:
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    assert "/api/v1/investigations" in r.json()["paths"]


def test_sse_stream_events(client: TestClient) -> None:
    r = client.post("/api/v1/investigations", json={
        "problem": "test stream", "files": {}})
    inv_id = r.json()["investigation_id"]
    with client.stream("GET",
                       f"/api/v1/investigations/{inv_id}/stream") as s:
        body = "".join(s.iter_text())
    assert "INVESTIGATION_STARTED" in body


def test_investigation_graph(client: TestClient) -> None:
    r = client.post("/api/v1/investigations", json={
        "problem": "Spark OOM on stage 3", "files": {}})
    inv_id = r.json()["investigation_id"]
    for _ in range(50):
        g = client.get(f"/api/v1/investigations/{inv_id}")
        if g.json().get("status") != "running":
            break
    r = client.get(f"/api/v1/investigations/{inv_id}/graph")
    assert r.status_code == 200
    body = r.json()
    assert "nodes" in body and "edges" in body
    for n in body["nodes"]:
        assert "node_id" in n and "kind" in n


def test_graph_404_missing(client: TestClient) -> None:
    assert client.get("/api/v1/investigations/nope/graph").status_code == 404
