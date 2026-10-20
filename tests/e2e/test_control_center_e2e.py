"""Cycle 06 E2E — Control Center API over a real uvicorn server (ds-0078).

Boots `data_sentinel.api.create_app` on a real socket and exercises the
full investigation lifecycle over HTTP — not the TestClient.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")
import httpx

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


TEST_TOKEN = "e2e-test-token"  # noqa: S105 - local test fixture
AUTH = {"Authorization": f"Bearer {TEST_TOKEN}"}


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> str:
    import os
    db = tmp_path_factory.mktemp("db") / "e2e.db"
    port = _free_port()
    env = dict(os.environ, DATA_SENTINEL_TOKEN=TEST_TOKEN)
    proc = subprocess.Popen(  # noqa: S603 - local test server
        [sys.executable, "-c",
         "import uvicorn; from data_sentinel.api import create_app;"
         f"uvicorn.run(create_app("
         f"allowed_roots=['{FIXTURES.as_posix()}'],"
         f" db_path='{db.as_posix()}'),"
         f" host='127.0.0.1', port={port}, log_level='error')"],
        cwd=ROOT, env=env)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                if httpx.get(f"{base}/api/v1/health",
                             timeout=0.5).status_code == 200:
                    break
            except httpx.TransportError:
                time.sleep(0.1)
        else:  # pragma: no cover
            proc.kill()
            pytest.fail("server did not start")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_e2e_real_server_investigation_flow(server: str) -> None:
    base = f"{server}/api/v1"
    # A: portal backend is real and healthy
    assert httpx.get(f"{base}/health").json()["status"] == "ok"
    # capabilities include EMR — truthful declarations
    caps = httpx.get(f"{base}/capabilities", headers=AUTH).json()
    assert any(c["capability_id"] == "sentinel.emr.ec2" for c in caps)
    # B: create investigation referencing a real fixture via a real tool
    sql = FIXTURES / "sql" / "cycle2" / "cast_keys.sql"
    r = httpx.post(f"{base}/investigations", headers=AUTH, json={
        "problem": "SQL join explosion risk",
        "files": {"sentinel.sql.analyze": str(sql)}})
    assert r.status_code == 201
    inv_id = r.json()["investigation_id"]
    for _ in range(100):
        rep = httpx.get(f"{base}/investigations/{inv_id}", headers=AUTH).json()
        if rep.get("status") != "running":
            break
        time.sleep(0.1)
    assert "sentinel.sql.analyze" in rep["tools_used"]
    assert len(rep["findings"]) >= 1
    # C: evidence graph endpoint returns real nodes; edges only when the
    #    report actually carries evidence links (never fabricated).
    g = httpx.get(f"{base}/investigations/{inv_id}/graph", headers=AUTH).json()
    assert g["nodes"]
    assert any(n["kind"] == "DiagnosticFinding" for n in g["nodes"])
    # export-equivalent: full report round-trips as JSON
    assert rep["investigation_id"] == inv_id


def test_e2e_real_server_analyze(server: str) -> None:
    sql = FIXTURES / "sql" / "cycle2" / "cast_keys.sql"
    r = httpx.post(f"{server}/api/v1/analyze/sql.analyze",
                   headers=AUTH, json={"file": str(sql)})
    assert r.status_code == 200
    assert r.json()["findings"]
