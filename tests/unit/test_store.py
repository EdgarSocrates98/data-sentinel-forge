"""Tests for the SQLite persistence layer."""

import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from data_sentinel.core.contracts import (
    AnalysisMode,
    ArtifactReference,
    DiagnosticReport,
    DiagnosticRequest,
    Evidence,
    EvidenceProvenance,
    Finding,
    FindingCategory,
    FindingStatus,
    Platform,
    Severity,
    SourceType,
)
from data_sentinel.core.exceptions import PersistenceError
from data_sentinel.persistence import SentinelStore, apply_migrations

NOW = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)


def make_request() -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=SourceType.LOG,
        artifact_references=[ArtifactReference(uri="job.log")],
        platform=Platform.AWS_GLUE,
        analysis_mode=AnalysisMode.BALANCED,
    )


def make_report(request_id: str = "req-1") -> DiagnosticReport:
    return DiagnosticReport(
        request_id=request_id,
        created_at=NOW,
        findings=[
            Finding(
                category=FindingCategory.OUT_OF_MEMORY,
                severity=Severity.HIGH,
                status=FindingStatus.CONFIRMED,
                explanation="x",
            ),
            Finding(
                category=FindingCategory.UNKNOWN,
                severity=Severity.INFO,
                status=FindingStatus.UNKNOWN,
                explanation="y",
            ),
        ],
        summary="2 findings",
    )


def make_evidence(excerpt: str = "line") -> Evidence:
    return Evidence(
        source="log",
        source_location="job.log:1",
        captured_at=NOW,
        content_hash="a" * 64,
        sanitized_excerpt=excerpt,
        provenance=EvidenceProvenance.OBSERVED,
        confidence=0.9,
    )


class TestStore:
    def test_save_and_get_report_round_trip(self, tmp_path: Path) -> None:
        with SentinelStore(tmp_path / "data") as store:
            report, request = make_report(), make_request()
            store.save_analysis(report, request, [make_evidence()])
            loaded = store.get_report(report.report_id)
            assert loaded is not None
            assert loaded == report

    def test_get_missing_report_returns_none(self, tmp_path: Path) -> None:
        with SentinelStore(tmp_path / "d") as store:
            assert store.get_report("nope") is None

    def test_list_reports_filters(self, tmp_path: Path) -> None:
        with SentinelStore(tmp_path / "d") as store:
            store.save_analysis(make_report("r1"), make_request())
            store.save_analysis(
                make_report("r2"),
                DiagnosticRequest(
                    source_type=SourceType.SQL_QUERY,
                    artifact_references=[ArtifactReference(uri="q.sql")],
                    platform=Platform.TRINO,
                ),
            )
            all_ = store.list_reports()
            assert len(all_) == 2
            logs = store.list_reports(source_type="log")
            assert len(logs) == 1 and logs[0].source_type == "log"
            trino = store.list_reports(platform="trino")
            assert len(trino) == 1

    def test_status_summary_counts(self, tmp_path: Path) -> None:
        with SentinelStore(tmp_path / "d") as store:
            store.save_analysis(make_report(), make_request())
            summary = store.list_reports()[0]
            assert "CONFIRMED:1" in summary.status_summary
            assert "UNKNOWN:1" in summary.status_summary

    def test_evidence_saved_and_loaded(self, tmp_path: Path) -> None:
        with SentinelStore(tmp_path / "d") as store:
            report = make_report()
            store.save_analysis(report, make_request())
            ev = make_evidence("excerpt")
            store.save_evidence(report.report_id, [ev])
            loaded = store.get_evidence(report.report_id)
            assert len(loaded) == 1
            assert loaded[0].evidence_id == ev.evidence_id
            assert loaded[0].content_hash == ev.content_hash

    def test_evidence_resanitized_on_save(self, tmp_path: Path) -> None:
        """save_evidence cannot bypass redaction — excerpt is re-sanitized."""
        with SentinelStore(tmp_path / "d") as store:
            report = make_report()
            store.save_analysis(report, make_request())
            hostile = make_evidence("login password=p4ssw0rd! done")
            store.save_evidence(report.report_id, [hostile])
            loaded = store.get_evidence(report.report_id)[0]
            assert "p4ssw0rd" not in loaded.sanitized_excerpt
            assert "«redacted:" in loaded.sanitized_excerpt


class TestMigrations:
    def test_migrations_apply_once(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "x.db")
        first = apply_migrations(conn)
        assert first == ["0001_init"]
        second = apply_migrations(conn)
        assert second == []

    def test_reopen_idempotent(self, tmp_path: Path) -> None:
        d = tmp_path / "d"
        with SentinelStore(d):
            pass
        with SentinelStore(d) as store:  # reopen runs migrations again cleanly
            assert store.get_report("x") is None

    def test_concurrent_open_read(self, tmp_path: Path) -> None:
        with SentinelStore(tmp_path / "d") as store:
            store.save_analysis(make_report(), make_request())
            other = sqlite3.connect(store.db_path)
            rows = other.execute("SELECT COUNT(*) FROM analyses").fetchone()
            assert rows[0] == 1
            other.close()


class TestErrors:
    @pytest.mark.skipif(sys.platform == "win32",
                        reason="chmod não impede escrita em diretório no Windows")
    def test_readonly_dir_raises_domain_error(self, tmp_path: Path) -> None:
        ro = tmp_path / "ro"
        ro.mkdir()
        ro.chmod(0o500)
        try:
            with pytest.raises((PersistenceError, OSError)):
                SentinelStore(ro / "sub")
        finally:
            ro.chmod(0o700)

    def test_corrupted_db_raises_domain_error(self, tmp_path: Path) -> None:
        d = tmp_path / "d"
        d.mkdir()
        (d / "sentinel.db").write_bytes(b"not a sqlite file at all")
        with pytest.raises(PersistenceError):
            SentinelStore(d)

    def test_all_sql_parameterized(self) -> None:
        """No f-string/format in SQL statements in store.py (grep guard)."""
        src = (
            Path(__file__).resolve().parents[2]
            / "src/data_sentinel/persistence/store.py"
        ).read_text(encoding="utf-8")
        for line in src.splitlines():
            if "execute(" in line and ("f\"" in line or "f'" in line):
                assert "FROM analyses" in line or "schema_migrations" in line
