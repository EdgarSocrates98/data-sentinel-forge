"""Local SQLite store for reports and sanitized evidence (§01.6).

Read-mostly single-user store: parameterized SQL only, no ORM, no
network, no server process. Raw file contents are never persisted —
only sanitized excerpts and content hashes.
"""

import os
import sqlite3
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from data_sentinel.core.contracts import (
    DiagnosticReport,
    DiagnosticRequest,
    Evidence,
)
from data_sentinel.core.exceptions import PersistenceError
from data_sentinel.core.security import sanitize_evidence_excerpt
from data_sentinel.persistence.migrations import apply_migrations

DB_FILENAME = "sentinel.db"


@dataclass(frozen=True)
class ReportSummary:
    report_id: str
    created_at: str
    source_type: str | None
    platform: str | None
    status_summary: str


def _status_summary(report: DiagnosticReport) -> str:
    counts: dict[str, int] = {}
    for finding in report.findings:
        counts[finding.status.value] = counts.get(finding.status.value, 0) + 1
    return ",".join(f"{k}:{v}" for k, v in sorted(counts.items()))


class SentinelStore:
    """SQLite-backed store for analyses and their evidence."""

    def __init__(self, store_dir: str | Path) -> None:
        self.dir = Path(store_dir).expanduser()
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            if os.name == "posix":
                self.dir.chmod(stat.S_IRWXU)
        except OSError as exc:
            raise PersistenceError(
                code="persistencia.diretorio",
                message=f"não foi possível criar o diretório de dados {self.dir}: {exc}",
                details={"dir": str(self.dir)},
            ) from exc
        self.db_path = self.dir / DB_FILENAME
        try:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
            apply_migrations(self._conn)
        except sqlite3.Error as exc:
            raise PersistenceError(
                code="persistencia.conexao",
                message=f"falha ao abrir o banco local {self.db_path}: {exc}",
                details={"db_path": str(self.db_path)},
            ) from exc

    @classmethod
    def from_config(cls, config: object) -> "SentinelStore":
        store_path = getattr(config, "store_path", "~/.local/share/data-sentinel")
        return cls(store_path)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SentinelStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def save_analysis(
        self,
        report: DiagnosticReport,
        request: DiagnosticRequest,
        evidence: Sequence[Evidence] = (),
    ) -> None:
        """Persist a report + its sanitized evidence atomically."""
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT OR REPLACE INTO analyses "
                    "(report_id, request_id, created_at, source_type, platform, "
                    "status_summary, report_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        report.report_id,
                        report.request_id,
                        report.created_at.isoformat(),
                        request.source_type.value,
                        request.platform.value,
                        _status_summary(report),
                        report.to_json(),
                    ),
                )
                for ev in evidence:
                    self._insert_evidence(report.report_id, ev)
        except sqlite3.Error as exc:
            raise PersistenceError(
                code="persistencia.escrita",
                message=f"falha ao salvar análise {report.report_id}: {exc}",
                details={"report_id": report.report_id},
            ) from exc

    def _insert_evidence(self, report_id: str, ev: Evidence) -> None:
        sanitized = sanitize_evidence_excerpt(ev.sanitized_excerpt, max_chars=8000)
        self._conn.execute(
            "INSERT OR REPLACE INTO evidence "
            "(evidence_id, report_id, source, source_location, captured_at, "
            "content_hash, sanitized_excerpt, provenance, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ev.evidence_id,
                report_id,
                ev.source,
                ev.source_location,
                ev.captured_at.isoformat(),
                ev.content_hash,
                sanitized,
                ev.provenance.value,
                ev.confidence,
            ),
        )

    def save_evidence(self, report_id: str, evidence: Sequence[Evidence]) -> None:
        try:
            with self._conn:
                for ev in evidence:
                    self._insert_evidence(report_id, ev)
        except sqlite3.Error as exc:
            raise PersistenceError(
                code="persistencia.escrita",
                message=f"falha ao salvar evidências do relatório {report_id}: {exc}",
                details={"report_id": report_id},
            ) from exc

    def get_report(self, report_id: str) -> DiagnosticReport | None:
        row = self._conn.execute(
            "SELECT report_json FROM analyses WHERE report_id = ?",
            (report_id,),
        ).fetchone()
        if row is None:
            return None
        return DiagnosticReport.from_json(row[0])

    def list_reports(
        self,
        *,
        limit: int = 50,
        source_type: str | None = None,
        platform: str | None = None,
    ) -> list[ReportSummary]:
        clauses, params = [], []
        if source_type:
            clauses.append("source_type = ?")
            params.append(source_type)
        if platform:
            clauses.append("platform = ?")
            params.append(platform)
        # clauses contains only static column predicates; values stay parameterized.
        query = (
            "SELECT report_id, created_at, source_type, platform, status_summary "
            "FROM analyses "
            + ("WHERE " + " AND ".join(clauses) if clauses else "")
            + " ORDER BY created_at DESC LIMIT ?"
        )
        rows = self._conn.execute(query, (*params, limit)).fetchall()
        return [
            ReportSummary(
                report_id=r[0],
                created_at=r[1],
                source_type=r[2],
                platform=r[3],
                status_summary=r[4],
            )
            for r in rows
        ]

    def get_evidence(self, report_id: str) -> list[Evidence]:
        rows = self._conn.execute(
            "SELECT evidence_id, source, source_location, captured_at, "
            "content_hash, sanitized_excerpt, provenance, confidence "
            "FROM evidence WHERE report_id = ?",
            (report_id,),
        ).fetchall()
        return [
            Evidence.parse(
                {
                    "evidence_id": r[0],
                    "source": r[1],
                    "source_location": r[2],
                    "captured_at": r[3],
                    "content_hash": r[4],
                    "sanitized_excerpt": r[5],
                    "provenance": r[6],
                    "confidence": r[7],
                }
            )
            for r in rows
        ]
