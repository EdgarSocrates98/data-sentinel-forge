"""ds-0091 / §2.4 — authentication hardening."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from data_sentinel.api.app import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_SENTINEL_TOKEN", "hardening-tok")
    c = TestClient(create_app(
        allowed_roots=[str(tmp_path)],
        db_path=tmp_path / "h.db"))
    return c


class TestRotation:
    def test_rotate_invalidates_old(self, client):
        client.headers["Authorization"] = "Bearer hardening-tok"
        r = client.post("/api/v1/auth/rotate")
        assert r.status_code == 200
        new = r.json()["token"]
        assert new != "hardening-tok"
        # token antigo rejeitado
        c2 = TestClient(client.app)
        c2.headers["Authorization"] = "Bearer hardening-tok"
        assert c2.get("/api/v1/investigations").status_code == 401
        # novo funciona
        c3 = TestClient(client.app)
        c3.headers["Authorization"] = f"Bearer {new}"
        assert c3.get("/api/v1/investigations").status_code == 200


class TestLockout:
    def test_bruteforce_lockout(self, client):
        c = TestClient(client.app)
        c.headers["Authorization"] = "Bearer wrong"
        for _ in range(10):
            assert c.get("/api/v1/investigations"
                         ).status_code == 401
        # 11ª tentativa → 429 mesmo com token ERRADO
        assert c.get("/api/v1/investigations").status_code == 429
        # e mesmo com token CERTO durante lockout
        c.headers["Authorization"] = "Bearer hardening-tok"
        assert c.get("/api/v1/investigations").status_code == 429


class TestIntegrity:
    def test_dangling_evidence_flagged(self):
        from data_sentinel.core.contracts.agent import InvestigationReport
        from data_sentinel.core.contracts.entities import Finding
        from data_sentinel.core.contracts.enums import FindingCategory, FindingStatus, Severity
        from data_sentinel.persistence.integrity import check_report_integrity
        rep = InvestigationReport(
            report_id="r", investigation_id="i", problem="p")
        rep.findings = [Finding(
            category=FindingCategory.OUT_OF_MEMORY,
            severity=Severity.HIGH,
            status=FindingStatus.CONFIRMED,
            explanation="x", evidence_ids=["ghost-ev"])]
        out = check_report_integrity(rep)
        assert not out.ok
        kinds = {i.kind for i in out.issues}
        assert "dangling_evidence" in kinds

    def test_clean_report_ok(self):
        from data_sentinel.core.contracts.agent import InvestigationReport
        from data_sentinel.core.contracts.entities import Evidence, Finding
        from data_sentinel.core.contracts.enums import FindingCategory, FindingStatus, Severity
        from data_sentinel.persistence.integrity import check_report_integrity
        rep = InvestigationReport(
            report_id="r", investigation_id="i", problem="p")
        from data_sentinel.core.contracts.enums import EvidenceProvenance
        rep.evidence = [Evidence(
            evidence_id="e1", source="test",
            source_location="mem", captured_at="2026-01-01T00:00:00Z",
            content_hash="h", sanitized_excerpt="x",
            provenance=EvidenceProvenance.OBSERVED,
            confidence=1.0)]
        rep.findings = [Finding(
            category=FindingCategory.OUT_OF_MEMORY,
            severity=Severity.HIGH,
            status=FindingStatus.PROBABLE,
            explanation="x", evidence_ids=["e1"])]
        rep.context["timeline"] = []
        out = check_report_integrity(rep)
        assert out.ok, [i.message for i in out.issues]
