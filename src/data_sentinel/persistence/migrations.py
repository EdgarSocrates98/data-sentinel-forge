"""Append-only, transactional SQL migrations (stdlib sqlite3 only)."""

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from data_sentinel.core.exceptions import PersistenceError

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_MIGRATION_NAME = re.compile(r"^\d{4}_.+\.sql$")


def _migration_files() -> list[Path]:
    return sorted(
        p
        for p in MIGRATIONS_DIR.iterdir()
        if p.is_file() and _MIGRATION_NAME.match(p.name)
    )


def apply_migrations(conn: sqlite3.Connection) -> list[str]:
    """Apply pending migrations in order. Idempotent. Returns applied versions."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    applied: set[str] = {
        row[0]
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }
    new_versions: list[str] = []
    for path in _migration_files():
        version = path.stem
        if version in applied:
            continue
        try:
            with conn:  # transaction: all-or-nothing per migration
                conn.executescript(path.read_text(encoding="utf-8"))
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, datetime.now(UTC).isoformat()),
                )
        except sqlite3.Error as exc:
            raise PersistenceError(
                code="persistencia.migracao_falhou",
                message=f"falha ao aplicar migração {version}: {exc}",
                details={"version": version, "file": str(path)},
            ) from exc
        new_versions.append(version)
    return new_versions
