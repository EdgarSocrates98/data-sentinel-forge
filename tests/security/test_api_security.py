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


# ---- cycle-08.1 independent review findings ----

def test_cors_preflight_on_protected_path(client: TestClient) -> None:
    """BLOCKER: CORS must be outermost — a preflight OPTIONS on a
    bearer-protected route must be answered by CORSMiddleware with
    Access-Control-* headers, never a bare 401 from bearer_auth
    (which would kill every authenticated browser call)."""
    r = client.options(
        "/api/v1/capabilities",
        headers={
            "Origin": "http://localhost:4200",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        })
    assert r.status_code == 200
    allow = r.headers.get("access-control-allow-origin")
    assert allow in {"http://localhost:4200", "*"}
    assert "authorization" in \
        r.headers.get("access-control-allow-headers", "").lower()
    # Non-allowed origins still get no grant
    r2 = client.options(
        "/api/v1/capabilities",
        headers={"Origin": "https://evil.example",
                 "Access-Control-Request-Method": "GET"})
    assert r2.headers.get("access-control-allow-origin") != \
        "https://evil.example"


def test_bearer_scheme_case_insensitive(client: TestClient) -> None:
    """RFC 7235: auth scheme is case-insensitive."""
    token = client.app.state.auth.token
    r = client.get("/api/v1/capabilities",
                   headers={"Authorization": f"bearer {token}"})
    assert r.status_code == 200


def test_bearer_prefix_without_space_rejected(client: TestClient) -> None:
    """`bearerXYZ` is not a Bearer credential — the space is required."""
    token = client.app.state.auth.token
    r = client.get("/api/v1/capabilities",
                   headers={"Authorization": f"bearer{token}"})
    assert r.status_code == 401


def test_malformed_content_length_400(client: TestClient) -> None:
    """A non-numeric Content-Length must not crash into a 500."""
    r = client.post("/api/v1/investigations",
                    headers={"content-length": "not-a-number"},
                    content=b"{}")
    assert r.status_code in {400, 422}  # never 500


def test_token_file_mode_enforced_on_rewrite(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A pre-existing permissive token file must be tightened to 0600
    on persist — O_CREAT mode alone cannot fix it (review)."""
    import os
    import stat
    tok = tmp_path / "session-token"
    tok.write_text("old", encoding="utf-8")
    tok.chmod(0o644)
    monkeypatch.setattr(api_mod, "_TOKEN_FILE", tok)
    api_mod.SessionAuth()
    if os.name != "nt":
        assert stat.S_IMODE(tok.stat().st_mode) == 0o600


def _snap(**kw: object) -> object:
    from data_sentinel.core.contracts.snapshot import ExecutionSnapshot
    base: dict[str, object] = {
        "snapshot_id": "s", "platform": "glue", "job_id": "j",
        "run_id": "r", "duration_s": 10.0, "input_bytes": 1_000,
        "failure": False, "provenance": "imported"}
    base.update(kw)
    return ExecutionSnapshot(**base)  # type: ignore[arg-type]


def test_watch_alert_ids_unique() -> None:
    """Alerts produced inside one millisecond must not share an id —
    `INSERT OR REPLACE` in the alerts table would silently overwrite."""
    from data_sentinel.watch.engine import AlertEngine, WatchDefinition
    eng = AlertEngine()
    w = WatchDefinition(watch_id="w", workload="x", platform="glue",
                        source="local", metrics=["duration_s"],
                        rule="regression")
    hist = [_snap(started_at=f"2024-01-{i:02d}T00:00:00Z")
            for i in range(1, 8)]
    cur = _snap(started_at="2024-02-01T00:00:00Z", duration_s=999.0,
                input_bytes=10**12)
    alerts = eng.evaluate(w, hist, cur)
    ids = [a.alert_id for a in alerts]
    assert len(ids) == len(set(ids)), ids


def test_recovery_releases_dedup_slot() -> None:
    """fail → recover → fail inside cooldown must alert again —
    recovery releases the dedup slot instead of stamping it."""
    from data_sentinel.watch.engine import AlertEngine, WatchDefinition
    eng = AlertEngine(cooldown_s=9999.0)
    w = WatchDefinition(watch_id="w", workload="x", platform="glue",
                        source="local", rule="failure")
    first = eng.evaluate(w, [], _snap(started_at="t1", failure=True))
    rec = eng.evaluate(w, [], _snap(started_at="t2"))
    second = eng.evaluate(w, [], _snap(started_at="t3", failure=True))
    assert any(a.kind == "job_failure" for a in first)
    assert any(a.recovered for a in rec)
    assert any(a.kind == "job_failure" and not a.recovered
               for a in second), "post-recovery failure suppressed"
