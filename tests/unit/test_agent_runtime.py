"""Agent runtime tests (ds-0051)."""

import pytest

from data_sentinel.agents import (
    AgentRuntime,
    BudgetExceededError,
    InvalidTransitionError,
    ProviderError,
    StubProvider,
    get_provider,
)
from data_sentinel.agents.providers import route_profile
from data_sentinel.core.contracts.agent import (
    AgentExecution,
    AgentState,
    AgentTask,
    InvestigationBudget,
    ModelRequest,
)


def _ex() -> AgentExecution:
    return AgentExecution(execution_id="e1", task_id="t1", agent_id="a1")


def test_valid_transitions() -> None:
    rt = AgentRuntime()
    ex = _ex()
    rt.transition(ex, AgentState.PLANNED)
    rt.transition(ex, AgentState.RUNNING)
    rt.transition(ex, AgentState.WAITING_FOR_EVIDENCE)
    rt.transition(ex, AgentState.RUNNING)
    rt.transition(ex, AgentState.VALIDATING)
    rt.transition(ex, AgentState.COMPLETED)
    assert ex.finished_at is not None


def test_invalid_transition_rejected() -> None:
    rt = AgentRuntime()
    ex = _ex()
    with pytest.raises(InvalidTransitionError):
        rt.transition(ex, AgentState.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        rt.transition(ex, AgentState.RUNNING)  # CREATED->RUNNING inválido


def test_terminal_states_are_final() -> None:
    rt = AgentRuntime()
    ex = _ex()
    rt.begin(ex)
    rt.transition(ex, AgentState.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        rt.transition(ex, AgentState.RUNNING)


def test_iteration_cap_forces_partial() -> None:
    rt = AgentRuntime(InvestigationBudget(max_iterations=3))
    task = AgentTask(task_id="t", agent_id="a", kind="investigate")
    ex = rt.run(task, lambda i: False)  # never finishes
    assert ex.state == AgentState.PARTIAL
    assert ex.iterations == 3


def test_tool_call_budget() -> None:
    rt = AgentRuntime(InvestigationBudget(max_tool_calls=2))
    ex = _ex()
    rt.begin(ex)
    rt.record_tool_call(ex)
    rt.record_tool_call(ex)
    with pytest.raises(BudgetExceededError):
        rt.record_tool_call(ex)
    assert ex.state == AgentState.BUDGET_EXCEEDED


def test_timeout_via_injected_clock() -> None:
    t = [0.0]
    rt = AgentRuntime(InvestigationBudget(timeout_seconds=10),
                      clock=lambda: t[0])
    ex = _ex()
    rt.begin(ex)
    t[0] = 11.0
    with pytest.raises(BudgetExceededError):
        rt.check(ex)


def test_run_completes() -> None:
    rt = AgentRuntime()
    task = AgentTask(task_id="t", agent_id="a", kind="investigate")
    ex = rt.run(task, lambda i: i >= 2)
    assert ex.state == AgentState.COMPLETED


def test_stub_provider() -> None:
    p = get_provider("stub")
    assert isinstance(p, StubProvider)
    r = p.complete(ModelRequest(prompt="hello world"))
    assert "stub" in r.text and r.tokens_in > 0


def test_unknown_provider() -> None:
    with pytest.raises(ProviderError):
        get_provider("nonexistent")


def test_route_profiles() -> None:
    assert route_profile("offline") == "none"
    assert route_profile("deep") == "local"
    assert route_profile("???") == "none"
