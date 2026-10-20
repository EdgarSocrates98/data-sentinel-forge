"""§9.5 — memória de investigações: resumos estruturados persistidos.

Persiste SOMENTE resumo estruturado sanitizado — nunca segredos,
nunca conteúdo integral de documentos.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from data_sentinel.agents.guardrails import redact_secrets
from data_sentinel.core.contracts.agent import InvestigationReport
from data_sentinel.persistence.investigations import DEFAULT_DB

_SCHEMA = """
CREATE TABLE IF NOT EXISTS investigation_memory (
    report_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    problem_hash TEXT NOT NULL,
    problem_excerpt TEXT NOT NULL,
    categories TEXT NOT NULL,
    severities TEXT NOT NULL,
    tools_used TEXT NOT NULL,
    findings_count INTEGER NOT NULL,
    limitations_count INTEGER NOT NULL,
    outcome TEXT NOT NULL
);
"""


@dataclass
class InvestigationSummary:
    report_id: str
    created_at: str
    problem_hash: str          # nunca o problema integral
    problem_excerpt: str       # ≤120 chars sanitizados
    categories: list[str] = field(default_factory=list)
    severities: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    findings_count: int = 0
    limitations_count: int = 0
    outcome: str = "completed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize(report: InvestigationReport,
              *, at: str | None = None) -> InvestigationSummary:
    cats = sorted({str(getattr(f.category, "value",
                               f.category))
                   for f in report.findings})
    sevs = sorted({str(getattr(f.severity, "value",
                               f.severity))
                   for f in report.findings})
    excerpt = redact_secrets(report.problem)[:120]
    digest = hashlib.sha256(report.problem.encode()).hexdigest()
    outcome = ("completed" if report.findings else
               "completed_no_findings")
    if report.limitations and not report.findings:
        outcome = "completed_with_limitations"
    return InvestigationSummary(
        report_id=report.report_id,
        created_at=at or _now(),
        problem_hash=digest,
        problem_excerpt=excerpt,
        categories=cats, severities=sevs,
        tools_used=list(report.tools_used),
        findings_count=len(report.findings),
        limitations_count=len(report.limitations),
        outcome=outcome)


def _now() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()


def remember(report: InvestigationReport,
             db_path: Path | str = DEFAULT_DB,
             *, at: str | None = None) -> InvestigationSummary:
    """Persiste o resumo — idempotente por report_id."""
    s = summarize(report, at=at)
    con = sqlite3.connect(str(db_path))
    try:
        con.executescript(_SCHEMA)
        con.execute(
            "INSERT OR REPLACE INTO investigation_memory "
            "(report_id, created_at, problem_hash, problem_excerpt,"
            " categories, severities, tools_used, findings_count,"
            " limitations_count, outcome)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (s.report_id, s.created_at, s.problem_hash,
             s.problem_excerpt, json.dumps(s.categories),
             json.dumps(s.severities), json.dumps(s.tools_used),
             s.findings_count, s.limitations_count, s.outcome))
        con.commit()
    finally:
        con.close()
    return s


def recall(db_path: Path | str = DEFAULT_DB,
           *, limit: int = 100) -> list[dict[str, Any]]:
    con = sqlite3.connect(str(db_path))
    try:
        con.executescript(_SCHEMA)
        rows = con.execute(
            "SELECT report_id, created_at, problem_hash,"
            " problem_excerpt, categories, severities, tools_used,"
            " findings_count, limitations_count, outcome"
            " FROM investigation_memory"
            " ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    finally:
        con.close()
    return [
        {"report_id": r[0], "created_at": r[1],
         "problem_hash": r[2], "problem_excerpt": r[3],
         "categories": json.loads(r[4]),
         "severities": json.loads(r[5]),
         "tools_used": json.loads(r[6]),
         "findings_count": r[7], "limitations_count": r[8],
         "outcome": r[9]}
        for r in rows]
