"""ds-0105 — SSE reliability over a real uvicorn server.

Multi-client fan-out, Last-Event-ID resume, replay integrity and
disconnect behavior — exercised over HTTP, not TestClient.
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

TEST_TOKEN = "e2e-sse-token"  # noqa: S105 - local test fixture
AUTH = {"Authorization": f"Bearer {TEST_TOKEN}"}


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> str:
    import os
    db = tmp_path_factory.mktemp("db") / "sse.db"
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


def _sse_events(base: str, inv_id: str,
                *, last_id: int | None = None,
                timeout: float = 15.0) -> list[tuple[int, str, str]]:
    """Read SSE frames until the stream ends. Returns (seq, event, data)."""
    headers = dict(AUTH)
    if last_id is not None:
        headers["Last-Event-ID"] = str(last_id)
    out: list[tuple[int, str, str]] = []
    eid: int | None = None
    etype = ""
    with httpx.stream(
            "GET", f"{base}/investigations/{inv_id}/stream",
            headers=headers, timeout=timeout) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if line.startswith("id:"):
                eid = int(line.split(":", 1)[1].strip())
            elif line.startswith("event:"):
                etype = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                out.append((eid or -1, etype, line.split(":", 1)[1].strip()))
                if etype in {"INVESTIGATION_COMPLETED",
                             "INVESTIGATION_FAILED"}:
                    return out
    return out


def _new_investigation(base: str) -> str:
    r = httpx.post(
        f"{base}/investigations",
        headers=AUTH,
        json={"problem": "analise o plano",
              "files": {"sentinel.spark.analyze_plan":
                        str(FIXTURES / "plans/sort_merge_join.txt")}},
        timeout=10)
    assert r.status_code == 201
    return str(r.json()["investigation_id"])


def _wait_terminal(base: str, inv_id: str,
                   timeout: float = 30.0) -> str:
    for _ in range(int(timeout * 10)):
        rec = httpx.get(f"{base}/investigations/{inv_id}",
                        headers=AUTH, timeout=5).json()
        if rec.get("status") in {"completed", "failed", "cancelled"}:
            return str(rec["status"])
        time.sleep(0.1)
    pytest.fail("investigation did not reach a terminal state")


def test_sse_replay_all_events_terminal(server: str) -> None:
    base = f"{server}/api/v1"
    inv = _new_investigation(base)
    _wait_terminal(base, inv)
    events = _sse_events(base, inv)
    assert events, "no events replayed"
    seqs = [e[0] for e in events]
    assert seqs == sorted(seqs), "out of order"
    assert len(seqs) == len(set(seqs)), "duplicate seq ids"
    assert events[0][1] == "INVESTIGATION_STARTED"
    assert events[-1][1] in {"INVESTIGATION_COMPLETED",
                             "INVESTIGATION_FAILED"}


def test_sse_two_clients_receive_identical_stream(server: str) -> None:
    """Fan-out: every client sees every event — no split delivery."""
    base = f"{server}/api/v1"
    inv = _new_investigation(base)
    _wait_terminal(base, inv)
    a = _sse_events(base, inv)
    b = _sse_events(base, inv)
    assert a == b, "clients diverged"
    assert len(a) >= 2


def test_sse_last_event_id_resumes_without_duplicates(server: str) -> None:
    base = f"{server}/api/v1"
    inv = _new_investigation(base)
    _wait_terminal(base, inv)
    full = _sse_events(base, inv)
    assert len(full) >= 2
    pivot = full[0][0]
    resumed = _sse_events(base, inv, last_id=pivot)
    assert resumed, "resume returned nothing"
    assert all(e[0] > pivot for e in resumed), \
        "replayed already-seen events"
    combined = full[:1] + resumed
    seqs = [e[0] for e in combined]
    assert len(seqs) == len(set(seqs)), "resume produced duplicates"
    assert {e[0] for e in combined} == {e[0] for e in full}, \
        "resume lost events"


def test_sse_unknown_investigation_404(server: str) -> None:
    r = httpx.get(f"{server}/api/v1/investigations/inv-nope/stream",
                  headers=AUTH, timeout=5)
    assert r.status_code == 404


def test_sse_reconnect_after_disconnect(server: str) -> None:
    """Client drops mid-stream; reconnect + Last-Event-ID continues
    cleanly — persisted seqs remain a strict superset."""
    base = f"{server}/api/v1"
    inv = _new_investigation(base)
    _wait_terminal(base, inv)
    full = _sse_events(base, inv)
    mid = len(full) // 2
    pivot = full[mid][0]
    resumed = _sse_events(base, inv, last_id=pivot)
    assert [e[0] for e in resumed] == [e[0] for e in full[mid + 1:]]
