"""RAG + memory tests (ds-0055)."""

from pathlib import Path

from data_sentinel.core.contracts.agent import InvestigationState
from data_sentinel.rag import InvestigationMemory, KnowledgeBase


def _kb() -> KnowledgeBase:
    kb = KnowledgeBase()
    kb.add_text("Iceberg snapshot expiration limpa metadados antigos",
                source="kb:iceberg")
    kb.add_text("Glue job falha por falta de memória no driver",
                source="kb:glue")
    kb.add_text("Política IAM nega s3:GetObject no bucket",
                source="kb:iam")
    return kb


def test_retrieve_ranks_and_keeps_provenance() -> None:
    r = _kb().search("falta de memória no driver do Glue")
    assert r.chunks
    assert r.chunks[0].source == "kb:glue"
    assert r.chunks[0].provenance
    assert r.method == "lexical-tfidf"


def test_retrieve_no_match_is_honest() -> None:
    r = _kb().search("zebra unicórnio quântico")
    assert not r.chunks
    assert "não deve inventar" in r.limitations[0]


def test_empty_query_limitation() -> None:
    r = _kb().search("a e o")
    assert r.limitations


def test_load_dir(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("lakeformation grant")
    (tmp_path / "b.md").write_text("kafka stream")
    kb = KnowledgeBase()
    assert kb.load_dir(tmp_path) == 2
    r = kb.search("lakeformation")
    assert r.chunks[0].source.endswith("a.md")


def test_memory_roundtrip(tmp_path: Path) -> None:
    m = InvestigationMemory(root=tmp_path)
    st = InvestigationState(investigation_id="inv-1")
    m.save(st)
    st2 = InvestigationState(investigation_id="inv-1")
    m.save(st2)
    loaded = m.load("inv-1")
    assert loaded is not None
    assert len(m.history("inv-1")) == 2
    assert m.load("inv-x") is None
