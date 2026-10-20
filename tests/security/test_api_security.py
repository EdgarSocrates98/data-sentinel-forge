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
    return TestClient(create_app(allowed_roots=[str(FIXTURES)]))


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
