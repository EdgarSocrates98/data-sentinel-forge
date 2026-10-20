"""Security tests for the Control Center API (ds-0078)."""

from __future__ import annotations

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import data_sentinel.api.app as api_mod  # noqa: E402
from data_sentinel.api import create_app  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app(allowed_roots=[str(FIXTURES)],
                     db_path=tmp_path / "sec.db")
    app.state.rate_buckets.clear()
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {app.state.auth.token}"
    return c


def test_path_traversal_variants(client: TestClient) -> None:
    for bad in ["../../etc/passwd", "/etc/passwd",
                str(FIXTURES.parent / "pyproject.toml")]:
        r = client.post("/api/v1/analyze/sql.analyze", json={"file": bad})
        assert r.status_code == 403, bad


def test_extension_allowlist(client: TestClient, tmp_path: Path) -> None:
    exe = FIXTURES / "evil.exe"
    exe.write_bytes(b"MZ")
    try:
        r = client.post("/api/v1/investigations", json={
            "problem": "x", "files": {"sentinel.sql.analyze": str(exe)}})
        assert r.status_code == 400
        # analyze endpoint applies the same allowlist (ds-0103)
        r = client.post("/api/v1/analyze/sql.analyze",
                        json={"file": str(exe)})
        assert r.status_code == 400
    finally:
        exe.unlink()


def test_payload_limit(client: TestClient) -> None:
    r = client.post(
        "/api/v1/investigations",
        content=b"x" * (api_mod.MAX_PAYLOAD + 1),
        headers={"content-type": "application/json"})
    assert r.status_code == 413


def test_rate_limit_enforced(client: TestClient) -> None:
    host = "testclient"
    client.app.state.rate_buckets[host] = [api_mod.time.time()] * 120
    r = client.get("/api/v1/health")
    assert r.status_code == 429


def test_audit_log_records(client: TestClient) -> None:
    api_mod._AUDIT_LOG.clear()
    client.get("/api/v1/health")
    assert any(e["path"] == "/api/v1/health" for e in api_mod._AUDIT_LOG)


def test_cors_restrictive(client: TestClient) -> None:
    r = client.options(
        "/api/v1/health",
        headers={"Origin": "https://evil.example",
                 "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") != \
        "https://evil.example"


def test_secret_redaction(client: TestClient) -> None:
    assert api_mod._redact(
        {"aws_secret_access_key": "AKIA", "nested": {"token": "t"},
         "ok": 1}) == {"aws_secret_access_key": "***",
                       "nested": {"token": "***"}, "ok": 1}


def test_no_glue_job_cancellation_endpoint(client: TestClient) -> None:
    spec = client.get("/api/openapi.json").json()
    paths = " ".join(spec["paths"].keys()).lower()
    assert "cancel" not in paths
    assert "delete" not in {m for p in spec["paths"].values()
                          for m in p}


def test_redaction_schema_classification() -> None:
    """§1.5: credential fields masked, usage metrics preserved."""
    creds = {"access_token": "abc", "refresh_token": "r"}
    for k in creds:
        assert api_mod._redact({k: creds[k]})[k] == "***"
    assert api_mod._redact({"tokens_used": 1234})["tokens_used"] == 1234
    assert api_mod._redact({"token_usage": 5})["token_usage"] == 5
    assert api_mod._redact({"input_tokens": 7})["input_tokens"] == 7
    assert api_mod._redact({"output_tokens": 9})["output_tokens"] == 9
    assert api_mod._redact({"token_budget": 100})["token_budget"] == 100


def test_auth_required(client: TestClient) -> None:
    """Protected endpoint rejects missing/wrong bearer."""
    c = TestClient(client.app)
    assert c.get("/api/v1/capabilities").status_code == 401
    c.headers["Authorization"] = "Bearer wrong"
    assert c.get("/api/v1/capabilities").status_code == 401
    # health stays open for liveness checks
    assert c.get("/api/v1/health").status_code == 200


def test_non_local_host_rejected(tmp_path: Path) -> None:
    app = create_app(allowed_roots=[str(FIXTURES)],
                     db_path=tmp_path / "h.db")
    c = TestClient(app, base_url="http://evil.example")
    r = c.get("/api/v1/health")
    assert r.status_code == 403


def test_cross_origin_mutation_rejected(client: TestClient) -> None:
    r = client.post("/api/v1/investigations",
                    headers={"Origin": "https://evil.example"},
                    json={"problem": "x", "files": {}})
    assert r.status_code == 403


# ---- ds-0103 backend hardening audit findings ----

def test_token_file_0600_from_creation(tmp_path: Path,
                                       monkeypatch: pytest.MonkeyPatch
                                       ) -> None:
    """Token file is born 0600 — no chmod-after-write window."""
    import os
    import stat
    tok = tmp_path / "session-token"
    monkeypatch.setattr(api_mod, "_TOKEN_FILE", tok)
    api_mod.SessionAuth()
    mode = stat.S_IMODE(tok.stat().st_mode)
    if os.name != "nt":  # Windows ACLs differ — POSIX check only
        assert mode == 0o600, oct(mode)


def test_stale_token_file_rejected(tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch
                                   ) -> None:
    """A token file older than TTL must not gain a fresh window."""
    import os

    tok = tmp_path / "session-token"
    tok.write_text("stale-token", encoding="utf-8")
    old = api_mod.time.time() - api_mod._TOKEN_TTL_S - 10
    os.utime(tok, (old, old))
    monkeypatch.setattr(api_mod, "_TOKEN_FILE", tok)
    auth = api_mod.SessionAuth()
    assert auth._token != "stale-token"  # noqa: S105


def test_fresh_token_file_reused(tmp_path: Path,
                                 monkeypatch: pytest.MonkeyPatch
                                 ) -> None:
    tok = tmp_path / "session-token"
    tok.write_text("fresh-token", encoding="utf-8")
    monkeypatch.setattr(api_mod, "_TOKEN_FILE", tok)
    auth = api_mod.SessionAuth()
    assert auth._token == "fresh-token"  # noqa: S105


def test_audit_log_rotates_never_stops() -> None:
    """Audit deque must keep recording past the bound."""
    api_mod._AUDIT_LOG.clear()
    for i in range(10_050):
        api_mod._audit("c", f"/p{i}", 200)
    assert len(api_mod._AUDIT_LOG) == 10_000
    assert api_mod._AUDIT_LOG[-1]["path"] == "/p10049"


def test_sse_subscriber_fanout(tmp_path: Path) -> None:
    """Two subscribers to the same investigation each get every event."""
    from data_sentinel.persistence.investigations import InvestigationStore
    st = api_mod.InvestigationState(
        store=InvestigationStore(tmp_path / "s.db"))
    st.store.create("inv-1", "p")
    q1 = st.subscribe("inv-1")
    q2 = st.subscribe("inv-1")
    st.emit("inv-1", "E1", {"a": 1})
    st.emit("inv-1", "E2", {"b": 2})
    assert [q1.get_nowait()["event"] for _ in range(2)] == ["E1", "E2"]
    assert [q2.get_nowait()["event"] for _ in range(2)] == ["E1", "E2"]
    st.unsubscribe("inv-1", q1)
    st.emit("inv-1", "E3", {})
    assert q1.empty()
    assert q2.get_nowait()["event"] == "E3"


def test_safe_error_strips_paths() -> None:
    err = api_mod._safe_error(
        ValueError(f"boom at {Path.home()}/.aws/credentials"))
    assert str(Path.home()) not in err
    assert "<path>" in err
    assert "ValueError" in err


def test_401_has_www_authenticate(tmp_path: Path) -> None:
    app = create_app(allowed_roots=[str(FIXTURES)],
                     db_path=tmp_path / "w.db")
    c = TestClient(app)
    r = c.get("/api/v1/capabilities")
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate") == "Bearer"
