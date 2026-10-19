-- 0001_init: analyses, evidence, schema_migrations
CREATE TABLE IF NOT EXISTS analyses (
    report_id      TEXT PRIMARY KEY,
    request_id     TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    source_type    TEXT,
    platform       TEXT,
    status_summary TEXT NOT NULL DEFAULT '',
    report_json    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id        TEXT PRIMARY KEY,
    report_id          TEXT NOT NULL REFERENCES analyses(report_id),
    source             TEXT NOT NULL,
    source_location    TEXT NOT NULL,
    captured_at        TEXT NOT NULL,
    content_hash       TEXT NOT NULL,
    sanitized_excerpt  TEXT NOT NULL,
    provenance         TEXT NOT NULL,
    confidence         REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evidence_report ON evidence(report_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at);
