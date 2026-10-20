"""Agent runtime — lifecycle + control plane (§3.1, §3.2).

Enforces valid state transitions and budget limits. No unbounded loops:
every iteration and tool call is accounted against InvestigationBudget.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from data_sentinel.core.contracts.agent import (
    AGENT_TRANSITIONS,
    AgentExecution,
    AgentState,
    AgentTask,
    InvestigationBudget,
)


class InvalidTransitionError(RuntimeError):
    pass


class BudgetExceededError(RuntimeError):
    pass


class CancelledError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class AgentRuntime:
    """Executes agent tasks under an explicit budget.

    The runtime never lets a task iterate past max_iterations or call
    tools past max_tool_calls; deadline is enforced against wall clock
    injected via ``_clock`` for testability.
    """

    def __init__(self, budget: InvestigationBudget | None = None,
                 *, clock: Callable[[], float] | None = None) -> None:
        self.budget = budget or InvestigationBudget()
        self._clock = clock
        self._deadline: float | None = None
        self.cancelled = False

    def _time(self) -> float:
        return self._clock() if self._clock is not None else time.monotonic()

    def transition(self, ex: AgentExecution, to: AgentState) -> None:
        allowed = AGENT_TRANSITIONS.get(ex.state, set())
        if to not in allowed:
            raise InvalidTransitionError(
                f"{ex.state.value} -> {to.value} não é transição válida")
        ex.state = to
        if to in (AgentState.RUNNING,) and ex.started_at is None:
            ex.started_at = _now()
        if to in (AgentState.COMPLETED, AgentState.PARTIAL,
                  AgentState.FAILED, AgentState.CANCELLED,
                  AgentState.BUDGET_EXCEEDED):
            ex.finished_at = _now()

    def begin(self, ex: AgentExecution) -> None:
        if self._deadline is None:
            self._deadline = self._time() + self.budget.timeout_seconds
        self.transition(ex, AgentState.PLANNED)
        self.transition(ex, AgentState.RUNNING)

    def check(self, ex: AgentExecution) -> None:
        """Called every iteration/tool call — raises on limit breach."""
        if self.cancelled:
            self.transition(ex, AgentState.CANCELLED)
            raise CancelledError("investigação cancelada")
        if self._deadline is not None and self._time() > self._deadline:
            self.transition(ex, AgentState.BUDGET_EXCEEDED)
            raise BudgetExceededError("timeout excedido")
        b = self.budget
        if (ex.iterations > b.max_iterations
                or ex.tool_calls > b.max_tool_calls
                or b.spent_tokens > b.max_tokens
                or (b.max_cost_usd > 0
                    and b.spent_cost_usd > b.max_cost_usd)):
            self.transition(ex, AgentState.BUDGET_EXCEEDED)
            raise BudgetExceededError(
                f"budget excedido: iters={ex.iterations}/"
                f"{b.max_iterations} tools={ex.tool_calls}/"
                f"{b.max_tool_calls}")

    def iterate(self, ex: AgentExecution) -> bool:
        """Returns False when the iteration cap is reached (terminal)."""
        ex.iterations += 1
        try:
            self.check(ex)
        except BudgetExceededError:
            return False
        return ex.iterations < self.budget.max_iterations

    def record_tool_call(self, ex: AgentExecution) -> None:
        ex.tool_calls += 1
        self.budget.spent_tool_calls += 1
        self.check(ex)

    def record_tokens(self, n_in: int, n_out: int) -> None:
        self.budget.spent_tokens += n_in + n_out

    def run(self, task: AgentTask, step: Callable[[int], bool],
            *, max_steps: int | None = None
            ) -> AgentExecution:
        """Drive ``step(iteration)->bool`` until done/capped.

        step returns True when the task finished its work, False to
        continue iterating.
        """
        ex = AgentExecution(
            execution_id=new_id("exec"), task_id=task.task_id,
            agent_id=task.agent_id)
        self.begin(ex)
        limit = max_steps if max_steps is not None else \
            self.budget.max_iterations
        try:
            for _ in range(limit):
                if not self.iterate(ex):
                    break
                if step(ex.iterations):
                    self.transition(ex, AgentState.COMPLETED)
                    return ex
            if ex.state == AgentState.RUNNING:
                # hit cap without finishing -> honest PARTIAL
                self.transition(ex, AgentState.PARTIAL)
        except (BudgetExceededError, CancelledError,
                InvalidTransitionError):
            raise
        except Exception:
            self.transition(ex, AgentState.FAILED)
            raise
        return ex
