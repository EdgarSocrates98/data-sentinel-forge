"""Cycle 05 E2E A-J — agentic pipeline end-to-end."""

import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from data_sentinel.agents.guardrails import (
    GuardrailError,
    PermissionClass,
    check_tool_permission,
    sanitize_untrusted,
)
from data_sentinel.agents.investigator import investigate
from data_sentinel.agents.runtime import AgentRuntime
from data_sentinel.agents.specialists import plan_tasks, route, specialist_descriptors
from data_sentinel.context import ContextCache, build_context
from data_sentinel.core.contracts.agent import AgentTask, InvestigationBudget, ToolInvocation
from data_sentinel.core.contracts.enums import FindingStatus, Severity
from data_sentinel.rag import InvestigationMemory, KnowledgeBase
from data_sentinel.reasoning import EvidenceValidator, RootCauseEngine
from data_sentinel.tools.registry import execute_tool

runner = CliRunner()
FX = Path(__file__).parent.parent / "fixtures"


def test_a_runtime_budget_enforced() -> None:
    rt = AgentRuntime(InvestigationBudget(max_iterations=2))
    task = AgentTask(task_id="t", agent_id="a", kind="investigate")
    ex = rt.run(task, lambda i: False)  # nunca termina
    from data_sentinel.core.contracts.agent import AgentState
    assert ex.state in {AgentState.PARTIAL,
                        AgentState.BUDGET_EXCEEDED}


def test_b_specialists_registered_and_routed() -> None:
    assert len(specialist_descriptors()) == 18  # 12 + 6 EMR (C05.1)
    assert route("glue oom") == ["glue-expert"]
    tasks = plan_tasks("spark skew", {"a": "f"})
    assert any(t.depends_on for t in tasks)


def test_c_tools_registry_execute(tmp_path: Path) -> None:
    f = tmp_path / "q.sql"
    f.write_text("SELECT * FROM a")
    res = execute_tool(ToolInvocation(
        invocation_id="e2e", tool_id="sentinel.sql.analyze",
        input={"file": str(f)}))
    assert res.ok
    assert "findings" in res.output or res.output


def test_d_mcp_stdio_roundtrip() -> None:
    pytest.importorskip("mcp")
    # coberto por tests/integration/test_mcp_stdio.py — aqui só importa
    from data_sentinel.mcp_server import create_server
    srv = create_server()
    assert srv is not None


def test_e_context_layers_and_budget() -> None:
    ctx = build_context(
        problem="p", evidence=[("ev", "src")],
        knowledge=[("k" * 90000, "kb")], token_limit=200)
    assert ctx.chunks and ctx.budget_notes


def test_f_rag_retrieval_and_memory(tmp_path: Path) -> None:
    kb = KnowledgeBase()
    kb.add_text("glue driver out of memory", source="kb:g")
    r = kb.search("driver memory")
    assert r.chunks and r.chunks[0].provenance
    m = InvestigationMemory(root=tmp_path)
    from data_sentinel.core.contracts.agent import InvestigationState
    m.save(InvestigationState(investigation_id="e2e-f"))
    assert m.load("e2e-f") is not None


def test_g_rca_and_validator_pipeline() -> None:
    from data_sentinel.core.contracts.entities import Finding
    from data_sentinel.core.contracts.enums import FindingCategory
    f = Finding(category=FindingCategory.OUT_OF_MEMORY,
                severity=Severity.CRITICAL,
                status=FindingStatus.CONFIRMED,
                explanation="driver OOM", evidence_ids=["e1"])
    assert EvidenceValidator().validate([f]).ok
    r = RootCauseEngine().analyze([f])
    assert r.primary and r.primary.status == "supported"


def test_h_guardrails_block_unsafe() -> None:
    with pytest.raises(GuardrailError):
        check_tool_permission("sentinel.sql.analyze",
                              PermissionClass.DESTRUCTIVE)
    out = sanitize_untrusted("AKIAIOSFODNN7EXAMPLE leaked")
    assert "AKIA" not in out


def test_i_investigate_cli_end_to_end(tmp_path: Path) -> None:
    f = tmp_path / "q.sql"
    f.write_text("SELECT * FROM t JOIN u ON t.a=u.a")
    rep = investigate("sql query lenta",
                      {"sentinel.sql.analyze": str(f)})
    assert rep.tools_used == ["sentinel.sql.analyze"]
    assert "validation" in rep.context


def test_j_full_cli_surface() -> None:
    from data_sentinel.cli import app
    for cmd in (["agents"], ["tools"], ["doctor"],
                ["capabilities", "--json"]):
        r = runner.invoke(app, cmd)
        assert r.exit_code == 0, cmd


def test_cache_bounded() -> None:
    c = ContextCache(max_entries=2, max_bytes=100)
    c.put("a", "x")
    c.put("b", "y")
    c.put("c", "z")
    assert c.evictions >= 1


def test_tool_benchmark_smoke(tmp_path: Path) -> None:
    f = tmp_path / "q.sql"
    f.write_text("SELECT * FROM a JOIN b ON a.x=b.x")
    t0 = time.perf_counter()
    for _ in range(5):
        execute_tool(ToolInvocation(
            invocation_id="b", tool_id="sentinel.sql.analyze",
            input={"file": str(f)}))
    ms = (time.perf_counter() - t0) / 5 * 1000
    assert ms < 5000  # sanidade, não regressão absurda
