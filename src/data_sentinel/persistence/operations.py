"""Operational persistence (§2.1 Cycle 08) — versioned SQLite schema.

Entities: ExecutionSnapshot, WatchDefinition, WatchExecution, Alert,
RemediationPlan, ApprovalRecord, OperationalAudit, investigation links.

Migrations via PRAGMA user_version — monotonic, append-only DDL,
never destructive. Same rules as investigations: parameterized SQL,
no ORM, no network, no raw file contents.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from data_sentinel.core.contracts.snapshot import ExecutionSnapshot
from data_sentinel.persistence.investigations import DEFAULT_DB
from data_sentinel.remediation.plans import RemediationPlan
from data_sentinel.watch.engine import Alert, WatchDefinition

SCHEMA_VERSION = 1

_MIGRATIONS: dict[int, str] = {
    1: """
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    job_id TEXT,
    run_id TEXT,
    started_at TEXT,
    payload_json TEXT NOT NULL,
    created_ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS snapshots_job ON snapshots(job_id, started_at);

CREATE TABLE IF NOT EXISTS watches (
    watch_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 0,
    created_ts REAL NOT NULL,
    updated_ts REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS watch_executions (
    exec_id INTEGER PRIMARY KEY AUTOINCREMENT,
    watch_id TEXT NOT NULL,
    ts REAL NOT NULL,
    alerts_json TEXT NOT NULL,
    result TEXT NOT NULL DEFAULT 'ok'
);
CREATE INDEX IF NOT EXISTS watch_exec ON watch_executions(watch_id, ts);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    watch_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    ts REAL NOT NULL,
    recovered INTEGER NOT NULL DEFAULT 0,
    findings_json TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS alerts_watch ON alerts(watch_id, ts);

CREATE TABLE IF NOT EXISTS remediation_plans (
    plan_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_ts REAL NOT NULL,
    updated_ts REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    approver TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS approvals_plan ON approvals(plan_id);

CREATE TABLE IF NOT EXISTS operational_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    ts REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS investigation_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id TEXT NOT NULL,
    entity_kind TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    created_ts REAL NOT NULL,
    UNIQUE (investigation_id, entity_kind, entity_id)
);
""",
}


def _migrate(conn: sqlite3.Connection) -> None:
    v = conn.execute("PRAGMA user_version").fetchone()[0]
    if v > SCHEMA_VERSION:
        raise RuntimeError(
            f"schema v{v} mais novo que o suportado "
            f"(v{SCHEMA_VERSION}) — upgrade do Sentinel necessário")
    for ver in range(v + 1, SCHEMA_VERSION + 1):
        conn.executescript(_MIGRATIONS[ver])
        conn.execute(f"PRAGMA user_version={ver}")


class OpsStore:
    """Thread-safe store for operational entities (§2.1)."""

    def __init__(self, db_path: Path | str = DEFAULT_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        with self._lock, self._conn:
            _migrate(self._conn)

    # ---- snapshots ----

    def save_snapshot(self, snap: ExecutionSnapshot) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO snapshots"
                " (snapshot_id, platform, job_id, run_id, started_at,"
                "  payload_json, created_ts) VALUES (?,?,?,?,?,?,?)",
                (snap.snapshot_id, snap.platform, snap.job_id,
                 snap.run_id, snap.started_at,
                 snap.model_dump_json(), time.time()))

    def get_snapshot(self, sid: str) -> ExecutionSnapshot | None:
        row = self._conn.execute(
            "SELECT payload_json FROM snapshots WHERE snapshot_id=?",
            (sid,)).fetchone()
        return (ExecutionSnapshot.model_validate_json(
            row["payload_json"]) if row else None)

    def list_snapshots(self, *, platform: str | None = None,
                       job_id: str | None = None
                       ) -> list[ExecutionSnapshot]:
        sql = "SELECT payload_json FROM snapshots WHERE 1=1"
        args: list[Any] = []
        if platform is not None:
            sql += " AND platform=?"
            args.append(platform)
        if job_id is not None:
            sql += " AND job_id=?"
            args.append(job_id)
        sql += " ORDER BY started_at"
        rows = self._conn.execute(sql, args).fetchall()
        return [ExecutionSnapshot.model_validate_json(r["payload_json"])
                for r in rows]

    def delete_snapshot(self, sid: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "DELETE FROM snapshots WHERE snapshot_id=?", (sid,))
            return cur.rowcount > 0

    # ---- watches ----

    def save_watch(self, w: WatchDefinition) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO watches"
                " (watch_id, payload_json, enabled, created_ts,"
                "  updated_ts)"
                " VALUES (?,?,?,COALESCE((SELECT created_ts FROM"
                " watches WHERE watch_id=?),?),?)",
                (w.watch_id, json.dumps(asdict(w)),
                 1 if w.enabled else 0, w.watch_id,
                 time.time(), time.time()))

    def get_watch(self, wid: str) -> WatchDefinition | None:
        row = self._conn.execute(
            "SELECT payload_json FROM watches WHERE watch_id=?",
            (wid,)).fetchone()
        if not row:
            return None
        d = json.loads(row["payload_json"])
        return WatchDefinition(**d)

    def list_watches(self) -> list[WatchDefinition]:
        rows = self._conn.execute(
            "SELECT payload_json FROM watches ORDER BY watch_id"
        ).fetchall()
        return [WatchDefinition(**json.loads(r["payload_json"]))
                for r in rows]

    def delete_watch(self, wid: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "DELETE FROM watches WHERE watch_id=?", (wid,))
            return cur.rowcount > 0

    # ---- watch executions & alerts ----

    def save_watch_execution(self, watch_id: str,
                             alerts: list[Alert],
                             result: str = "ok") -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO watch_executions"
                " (watch_id, ts, alerts_json, result) VALUES (?,?,?,?)",
                (watch_id, time.time(),
                 json.dumps([asdict(a) for a in alerts]), result))
            for a in alerts:
                self._conn.execute(
                    "INSERT OR REPLACE INTO alerts"
                    " (alert_id, watch_id, kind, severity, message, ts,"
                    "  recovered, findings_json)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (a.alert_id, a.watch_id, a.kind, a.severity,
                     a.message, a.ts, 1 if a.recovered else 0,
                     json.dumps(a.findings)))

    def list_watch_executions(self, watch_id: str,
                              *, limit: int = 100
                              ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT exec_id, ts, alerts_json, result FROM"
            " watch_executions WHERE watch_id=? ORDER BY ts DESC"
            " LIMIT ?", (watch_id, limit)).fetchall()
        return [{"exec_id": r["exec_id"], "ts": r["ts"],
                 "alerts": json.loads(r["alerts_json"]),
                 "result": r["result"]} for r in rows]

    def list_alerts(self, *, watch_id: str | None = None,
                    limit: int = 500) -> list[dict[str, Any]]:
        if watch_id:
            rows = self._conn.execute(
                "SELECT * FROM alerts WHERE watch_id=?"
                " ORDER BY ts DESC LIMIT ?",
                (watch_id, limit)).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM alerts ORDER BY ts DESC LIMIT ?",
                (limit,)).fetchall()
        return [dict(r) | {"recovered": bool(r["recovered"]),
                           "findings": json.loads(r["findings_json"])}
                for r in rows]

    # ---- remediation plans & approvals ----

    def save_plan(self, plan: RemediationPlan) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO remediation_plans"
                " (plan_id, state, payload_json, created_ts,"
                "  updated_ts)"
                " VALUES (?,?,?,COALESCE((SELECT created_ts FROM"
                " remediation_plans WHERE plan_id=?),?),?)",
                (plan.plan_id, str(plan.state),
                 plan.model_dump_json(), plan.plan_id,
                 time.time(), time.time()))

    def get_plan(self, pid: str) -> RemediationPlan | None:
        row = self._conn.execute(
            "SELECT payload_json FROM remediation_plans"
            " WHERE plan_id=?", (pid,)).fetchone()
        return (RemediationPlan.model_validate_json(
            row["payload_json"]) if row else None)

    def list_plans(self) -> list[RemediationPlan]:
        rows = self._conn.execute(
            "SELECT payload_json FROM remediation_plans"
            " ORDER BY created_ts").fetchall()
        return [RemediationPlan.model_validate_json(r["payload_json"])
                for r in rows]

    def save_approval(self, plan_id: str, approver: str,
                      decision: str, reason: str | None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO approvals"
                " (plan_id, approver, decision, reason, ts)"
                " VALUES (?,?,?,?,?)",
                (plan_id, approver, decision, reason, time.time()))

    def list_approvals(self, plan_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM approvals WHERE plan_id=? ORDER BY ts",
            (plan_id,)).fetchall()
        return [dict(r) for r in rows]

    # ---- audit & links ----

    def audit(self, actor: str, action: str,
              detail: dict[str, Any] | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO operational_audit"
                " (actor, action, detail_json, ts) VALUES (?,?,?,?)",
                (actor, action, json.dumps(detail or {}),
                 time.time()))

    def list_audit(self, *, limit: int = 500) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM operational_audit ORDER BY audit_id DESC"
            " LIMIT ?", (limit,)).fetchall()
        return [dict(r) | {"detail": json.loads(r["detail_json"])}
                for r in rows]

    def link(self, investigation_id: str, entity_kind: str,
             entity_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO investigation_links"
                " (investigation_id, entity_kind, entity_id,"
                "  created_ts) VALUES (?,?,?,?)",
                (investigation_id, entity_kind, entity_id,
                 time.time()))

    def links_for(self, investigation_id: str
                  ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT entity_kind, entity_id FROM investigation_links"
            " WHERE investigation_id=?",
            (investigation_id,)).fetchall()
        return [dict(r) for r in rows]

    # ---- retention ----

    def prune(self, *, snapshots_older_than_s: float | None = None,
              alerts_older_than_s: float | None = None
              ) -> dict[str, int]:
        """Retention autorizada e auditável (§10.2)."""
        removed: dict[str, int] = {}
        now = time.time()
        with self._lock, self._conn:
            if snapshots_older_than_s is not None:
                cutoff = _iso_cutoff(snapshots_older_than_s)
                cur = self._conn.execute(
                    "DELETE FROM snapshots WHERE started_at < ?",
                    (cutoff,))
                removed["snapshots"] = cur.rowcount
            if alerts_older_than_s is not None:
                cur = self._conn.execute(
                    "DELETE FROM alerts WHERE ts < ?",
                    (now - alerts_older_than_s,))
                removed["alerts"] = cur.rowcount
        return removed

    def close(self) -> None:
        self._conn.close()


def _iso_cutoff(older_s: float) -> str:
    from datetime import UTC, datetime, timedelta
    return (datetime.now(UTC)
            - timedelta(seconds=older_s)).isoformat()
