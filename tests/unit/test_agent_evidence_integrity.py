"""ds-0106 — agent evidence integrity + determinism.

Every evidence reference emitted by the investigation layer must
resolve to a real Evidence object in the report — the agent never
invents evidence. And the deterministic path must stay LLM-free.
"""

from __future__ import annotations

import ast
from pathlib import Path

from data_sentinel.agents.investigator import investigate

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"
SRC = ROOT / "src" / "data_sentinel"

_LLM_IMPORTS = {
    "openai", "anthropic", "litellm", "langchain", "langchain_core",
    "langchain_community", "ollama", "cohere", "mistralai",
    "google.generativeai", "vertexai", "bedrock", "transformers",
    "sentence_transformers", "instructor", "guidance",
}


def test_investigation_evidence_refs_resolve() -> None:
    """Every evidence_ids / supporting_evidence reference resolves to
    a real Evidence in rep.evidence — never a dangling pointer."""
    rep = investigate(
        "analise o plano spark e a query",
        {"sentinel.spark.analyze_plan":
         str(FIXTURES / "plans/sort_merge_join.txt"),
         "sentinel.sql.analyze":
         str(FIXTURES / "sql/implicit_join.sql")})
    known = {e.evidence_id for e in rep.evidence}
    dangling: list[str] = []
    for f in rep.findings:
        dangling.extend(
            f"{f.finding_id}:{eid}" for eid in f.evidence_ids
            if eid not in known)
    for h in rep.hypotheses_supported + rep.hypotheses_refuted:
        dangling.extend(
            f"{h.hypothesis_id}:{eid}" for eid in h.supporting_evidence
            if eid not in known)
        dangling.extend(
            f"{h.hypothesis_id}:{eid}" for eid in h.contradicting_evidence
            if eid not in known)
    assert not dangling, f"evidence refs não resolvidas: {dangling}"


def test_confirmed_findings_have_resolvable_evidence() -> None:
    """CONFIRMED sem evidência resolvível é proibido (§4)."""
    from data_sentinel.core.contracts.enums import FindingStatus
    rep = investigate(
        "analise o plano",
        {"sentinel.spark.analyze_plan":
         str(FIXTURES / "plans/sort_merge_join.txt")})
    known = {e.evidence_id for e in rep.evidence}
    bad = [
        f.finding_id for f in rep.findings
        if f.status == FindingStatus.CONFIRMED
        and (not f.evidence_ids
             or any(e not in known for e in f.evidence_ids))]
    assert not bad, f"CONFIRMED sem evidência resolvível: {bad}"


def test_no_llm_imports_in_src() -> None:
    """The deterministic path must not depend on any LLM SDK — a
    static guarantee, not a convention."""
    hits: list[str] = []
    for py in SRC.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mod = ""
            if isinstance(node, ast.Import):
                mod = node.names[0].name
            elif isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
            top = mod.split(".")[0]
            if mod and (mod in _LLM_IMPORTS or top in _LLM_IMPORTS):
                hits.append(f"{py.relative_to(SRC)}:{node.lineno} {mod}")
    assert not hits, f"import de LLM em src: {hits}"
