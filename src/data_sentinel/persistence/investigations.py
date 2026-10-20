"""Persistent investigation engine — SQLite stdlib store (ds-0081, §2).

Lives alongside ``persistence.store.SentinelStore`` (reports/evidence);
this module owns the investigation lifecycle + event log tables.

Concurrency: WAL journal + threading lock — safe for the uvicorn
asyncio thread + worker threads issuing writes concurrently.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

DEFAULT_DB = Path.home() / ".data-sentinel" / "sentinel.db"


class State(StrEnum):
    """Investigation lifecycle states (§2.2)."""
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"


VALID_TRANSITIONS: dict[State, frozenset[State]] = {
    State.CREATED: frozenset({State.QUEUED, State.RUNNING,
                            State.CANCELLED, State.FAILED}),
    State.QUEUED: frozenset({State.RUNNING, State.CANCELLED,
                             State.FAILED, State.INTERRUPTED}),
    State.RUNNING: frozenset({State.PAUSED, State.COMPLETED,
                              State.FAILED, State.CANCELLED,
                              State.INTERRUPTED}),
    State.PAUSED: frozenset({State.RUNNING, State.CANCELLED,
                             State.INTERRUPTED}),
    State.COMPLETED: frozenset(),
    State.FAILED: frozenset(),
    State.CANCELLED: frozenset(),
    # INTERRUPTED → QUEUED only via explicit user resume (never silent).
    State.INTERRUPTED: frozenset({State.QUEUED}),
}


@dataclass
class InvestigationRecord:
    investigation_id: str
    state: State
    problem: str
    created_at: float
    updated_at: float
    report: dict[str, Any] | None = None
    meta: dict[str, Any] = field(default_factory=dict)


_DDL = """
CREATE TABLE IF NOT EXISTS investigations (
    investigation_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    problem TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    report_json TEXT,
    meta_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER NOT NULL,
    investigation_id TEXT NOT NULL,
    event TEXT NOT NULL,
    data_json TEXT NOT NULL,
    ts REAL NOT NULL,
    PRIMARY KEY (investigation_id, seq)
);
CREATE INDEX IF NOT EXISTS events_inv ON events(investigation_id, seq);
"""


class InvestigationStore:
    """Thread-safe SQLite store for investigations + events."""

    def __init__(self, db_path: Path | str = DEFAULT_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        with self._lock, self._conn:
            self._conn.executescript(_DDL)
            # §2.3: RUNNING/QUEUED at boot → INTERRUPTED; resume is
            # explicit only — nothing restarts silently.
            self._conn.execute(
                "UPDATE investigations SET state=?, updated_at=? "
                "WHERE state IN (?, ?)",
                (State.INTERRUPTED.value, time.time(),
                 State.RUNNING.value, State.QUEUED.value))

    # ---- investigations ----

    def create(self, inv_id: str, problem: str,
               meta: dict[str, Any] | None = None) -> InvestigationRecord:
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO investigations "
                "(investigation_id, state, problem, created_at, "
                " updated_at, meta_json) VALUES (?,?,?,?,?,?)",
                (inv_id, State.CREATED.value, problem, now, now,
                 json.dumps(meta or {})))
        return InvestigationRecord(inv_id, State.CREATED, problem,
                                   now, now, meta=meta or {})

    def transition(self, inv_id: str, to: State) -> None:
        """Apply a validated state transition (§2.2)."""
        rec = self.get(inv_id)
        if rec is None:
            raise KeyError(inv_id)
        if to not in VALID_TRANSITIONS[rec.state]:
            raise ValueError(
                f"invalid transition {rec.state} -> {to}")
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE investigations SET state=?, updated_at=? "
                "WHERE investigation_id=?",
                (to.value, time.time(), inv_id))
        rec.state = to

    def save_report(self, inv_id: str, report: dict[str, Any]) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE investigations SET report_json=?, updated_at=? "
                "WHERE investigation_id=?",
                (json.dumps(report), time.time(), inv_id))

    def get(self, inv_id: str) -> InvestigationRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM investigations WHERE investigation_id=?",
                (inv_id,)).fetchone()
        return self._to_record(row) if row else None

    def list_all(self, *, limit: int = 200) -> list[InvestigationRecord]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM investigations "
                "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._to_record(r) for r in rows]

    def _to_record(self, row: sqlite3.Row) -> InvestigationRecord:
        report = json.loads(row["report_json"]) \
            if row["report_json"] else None
        return InvestigationRecord(
            row["investigation_id"], State(row["state"]),
            row["problem"], row["created_at"], row["updated_at"],
            report=report, meta=json.loads(row["meta_json"]))

    # ---- events (§2.4) ----

    def emit(self, inv_id: str, event: str, data: dict[str, Any]) -> int:
        """Append event with next monotonic sequence; returns seq."""
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT COALESCE(MAX(seq),0)+1 AS n FROM events "
                "WHERE investigation_id=?", (inv_id,)).fetchone()
            seq: int = row["n"]
            self._conn.execute(
                "INSERT INTO events VALUES (?,?,?,?,?)",
                (seq, inv_id, event, json.dumps(data), time.time()))
            return seq

    def events(self, inv_id: str, *, after_seq: int = 0,
               limit: int = 1000) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT seq, event, data_json, ts FROM events "
                "WHERE investigation_id=? AND seq>? ORDER BY seq "
                "LIMIT ?", (inv_id, after_seq, limit)).fetchall()
        return [{"seq": r["seq"], "event": r["event"],
                 "data": json.loads(r["data_json"]), "ts": r["ts"]}
                for r in rows]

    # ---- retention (§2.5) ----

    def prune(self, *, older_than_s: float | None = None,
              max_investigations: int | None = None) -> int:
        """Delete oldest investigations (+events). Returns count."""
        removed: list[str] = []
        with self._lock, self._conn:
            if older_than_s is not None:
                rows = self._conn.execute(
                    "SELECT investigation_id FROM investigations "
                    "WHERE created_at < ?",
                    (time.time() - older_than_s,)).fetchall()
                removed += [r["investigation_id"] for r in rows]
            if max_investigations is not None:
                rows = self._conn.execute(
                    "SELECT investigation_id FROM investigations "
                    "ORDER BY created_at DESC LIMIT -1 OFFSET ?",
                    (max_investigations,)).fetchall()
                removed += [r["investigation_id"] for r in rows]
            for inv_id in set(removed):
                self._conn.execute(
                    "DELETE FROM events WHERE investigation_id=?",
                    (inv_id,))
                self._conn.execute(
                    "DELETE FROM investigations "
                    "WHERE investigation_id=?", (inv_id,))
        return len(set(removed))

    def delete(self, inv_id: str) -> bool:
        """Authorized local deletion of one investigation."""
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM events WHERE investigation_id=?", (inv_id,))
            cur = self._conn.execute(
                "DELETE FROM investigations WHERE investigation_id=?",
                (inv_id,))
        return cur.rowcount > 0

    def close(self) -> None:
        self._conn.close()
