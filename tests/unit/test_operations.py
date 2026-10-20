"""ds-0026 — MERGE/APPEND/incremental intelligence."""

from pathlib import Path

from data_sentinel.analyzers.protocol import InputFile
from data_sentinel.analyzers.registry import registry
from data_sentinel.core.contracts.entities import (
    ArtifactReference,
    DiagnosticRequest,
)
from data_sentinel.core.contracts.enums import (
    FindingStatus,
    Platform,
    SourceType,
)

FX = Path("fixtures/operations")


def _run(name: str):
    p = FX / name
    t = p.read_text()
    req = DiagnosticRequest(
        source_type=SourceType.SQL_QUERY,
        artifact_references=[ArtifactReference(uri="file://op")],
        platform=Platform.AWS_GLUE,
    )
    return registry.get("lakehouse.operation").analyze(
        req, [InputFile(path=p, text=t, size_bytes=len(t.encode()))]
    )


def test_registered():
    assert registry.get("lakehouse.operation").analyzer_id == "lakehouse.operation"


def test_merge_clean_no_dup_finding():
    r = _run("merge_ok.sql")
    assert not any("duplicadas" in f.explanation for f in r.findings)
    # mas unicidade não declarada → UNKNOWN sobre unicidade
    assert any("Unicidade" in f.explanation for f in r.findings)


def test_merge_declared_dups_confirmed():
    r = _run("merge_dups.json")
    f = next(f for f in r.findings if "duplicadas" in f.explanation)
    assert f.status == FindingStatus.CONFIRMED
    assert "1400" in f.explanation
    assert f.evidence_ids


def test_merge_or_condition_possible_ambiguity():
    r = _run("merge_or.sql")
    f = next(f for f in r.findings if "OR" in f.explanation or "ambígu" in f.explanation)
    assert f.status == FindingStatus.POSSIBLE


def test_append_idempotency_possible():
    r = _run("append.sql")
    f = next(f for f in r.findings if "APPEND" in f.explanation)
    assert f.status == FindingStatus.POSSIBLE
    assert "reprocessamento" in f.explanation


def test_delete_without_where_confirmed():
    r = _run("delete_full.sql")
    f = next(f for f in r.findings if "sem predicado" in f.explanation)
    assert f.status == FindingStatus.CONFIRMED


def test_commit_conflict_from_log_confirmed():
    r = _run("commit_conflict.json")
    f = next(f for f in r.findings if "Conflito de commit" in f.explanation)
    assert f.status == FindingStatus.CONFIRMED


def test_declared_unique_skips_dup_unknown():
    r = _run("commit_conflict.json")  # source_key_unique: True
    assert not any("Unicidade" in f.explanation for f in r.findings)


def test_unparseable_sql_limitation_not_crash():
    r = _run("bad.sql")
    assert any("SQL" in lim for lim in r.limitations)


def test_operations_metadata():
    r = _run("merge_ok.sql")
    assert r.metadata["operations"][0]["operation"] == "merge"
