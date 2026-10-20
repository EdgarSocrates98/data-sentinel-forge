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
def client() -> TestClient:
    api_mod._RATE_BUCKETS.clear()
    app = create_app(allowed_roots=[str(FIXTURES)])
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {app.state.auth.token}"
    return c


def test_path_traversal_variants(client: TestClient) -> None:
    for bad in ["../../etc/passwd", "/etc/passwd",
                str(FIXTURES.parent / "pyproject.toml")]:
        r = client.post("/api/v1/analyze/sql.analyze", json={"file": bad})
        assert r.status_code == 403, bad


def test_extension_allowlist(client: TestClient, tmp_path: Path) -> None:
    api_mod._RATE_BUCKETS.clear()
    exe = FIXTURES / "evil.exe"
    exe.write_bytes(b"MZ")
    try:
        r = client.post("/api/v1/investigations", json={
            "problem": "x", "files": {"sentinel.sql.analyze": str(exe)}})
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
    api_mod._RATE_BUCKETS[host] = [api_mod.time.time()] * 120
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


def test_non_local_host_rejected() -> None:
    app = create_app(allowed_roots=[str(FIXTURES)])
    c = TestClient(app, base_url="http://evil.example")
    r = c.get("/api/v1/health")
    assert r.status_code == 403


def test_cross_origin_mutation_rejected(client: TestClient) -> None:
    r = client.post("/api/v1/investigations",
                    headers={"Origin": "https://evil.example"},
                    json={"problem": "x", "files": {}})
    assert r.status_code == 403
