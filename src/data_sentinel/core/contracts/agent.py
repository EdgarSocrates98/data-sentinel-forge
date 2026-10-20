"""Cycle 05 — agentic contracts (§3, §5.1, §8.1).

Versioned models for the agent runtime, tool registry, investigation
state and hypotheses. All ContractModel: strict, forbid extras.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from data_sentinel.core.contracts.entities import (
    ContractModel,
    Evidence,
    Finding,
    OptimizationRecommendation,
    UTCDateTime,
)


class AgentState(StrEnum):
    CREATED = "created"
    PLANNED = "planned"
    RUNNING = "running"
    WAITING_FOR_EVIDENCE = "waiting_for_evidence"
    VALIDATING = "validating"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BUDGET_EXCEEDED = "budget_exceeded"


# valid transitions: source -> allowed targets
AGENT_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.CREATED: {AgentState.PLANNED, AgentState.CANCELLED,
                       AgentState.FAILED},
    AgentState.PLANNED: {AgentState.RUNNING, AgentState.CANCELLED,
                         AgentState.FAILED},
    AgentState.RUNNING: {AgentState.WAITING_FOR_EVIDENCE,
                         AgentState.VALIDATING, AgentState.COMPLETED,
                         AgentState.PARTIAL, AgentState.FAILED,
                         AgentState.CANCELLED, AgentState.BUDGET_EXCEEDED},
    AgentState.WAITING_FOR_EVIDENCE: {AgentState.RUNNING,
                                      AgentState.CANCELLED,
                                      AgentState.BUDGET_EXCEEDED,
                                      AgentState.FAILED},
    AgentState.VALIDATING: {AgentState.COMPLETED, AgentState.PARTIAL,
                            AgentState.FAILED, AgentState.RUNNING},
    AgentState.COMPLETED: set(),
    AgentState.PARTIAL: set(),
    AgentState.FAILED: set(),
    AgentState.CANCELLED: set(),
    AgentState.BUDGET_EXCEEDED: set(),
}


class ToolPermission(StrEnum):
    LOCAL_READ = "local_read"
    CLOUD_READ = "cloud_read"
    NETWORK_RETRIEVAL = "network_retrieval"
    FILE_WRITE = "file_write"          # report artifacts only, explicit
    CLOUD_WRITE = "cloud_write"        # unavailable this cycle
    DESTRUCTIVE = "destructive"        # unavailable this cycle


BLOCKED_PERMISSIONS = {ToolPermission.CLOUD_WRITE,
                       ToolPermission.DESTRUCTIVE}


class ModelProfile(StrEnum):
    OFFLINE = "offline"
    ECONOMY = "economy"
    BALANCED = "balanced"
    DEEP = "deep"


# --- tools -----------------------------------------------------------

class ToolDescriptor(ContractModel):
    tool_id: str = Field(min_length=1)       # sentinel.spark.analyze_plan
    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    permissions: list[ToolPermission] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    network_required: bool = False
    estimated_cost: str = "low"              # low|medium|high
    timeout_seconds: float = 30.0
    output_limitations: list[str] = Field(default_factory=list)
    version: str = "1.0.0"


class ToolInvocation(ContractModel):
    invocation_id: str = Field(min_length=1)
    tool_id: str = Field(min_length=1)
    agent_id: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    started_at: UTCDateTime | None = None


class ToolResult(ContractModel):
    invocation_id: str = Field(min_length=1)
    tool_id: str = ""
    ok: bool
    output: Any = None
    error: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    truncated: bool = False
    limitations: list[str] = Field(default_factory=list)


class ToolExecutionContext(ContractModel):
    investigation_id: str
    agent_id: str = ""
    budget: InvestigationBudget | None = None
    allowed_permissions: set[str] = Field(default_factory=set)
    dry_run: bool = False
    deadline_epoch: float | None = None


# --- agents ----------------------------------------------------------

class AgentCapability(ContractModel):
    capability_id: str = Field(min_length=1)
    description: str = ""
    input_kinds: list[str] = Field(default_factory=list)
    output_kinds: list[str] = Field(default_factory=list)


class AgentDescriptor(ContractModel):
    agent_id: str = Field(min_length=1)
    name: str
    responsibility: str
    capabilities: list[AgentCapability] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    policy: str = "deterministic_first"
    max_iterations: int = 8
    max_tool_calls: int = 20
    model_profile: ModelProfile = ModelProfile.OFFLINE
    version: str = "1.0.0"


class AgentTask(ContractModel):
    task_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)          # investigate|validate|synthesize
    input: dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    depends_on: list[str] = Field(default_factory=list)


class AgentExecution(ContractModel):
    execution_id: str = Field(min_length=1)
    task_id: str
    agent_id: str
    state: AgentState = AgentState.CREATED
    started_at: UTCDateTime | None = None
    finished_at: UTCDateTime | None = None
    iterations: int = 0
    tool_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    error: str = ""


class AgentDecision(ContractModel):
    decision_id: str = Field(min_length=1)
    execution_id: str = ""
    kind: str = Field(min_length=1)          # select_tool|delegate|conclude
    rationale: str = ""
    alternatives: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class AgentObservation(ContractModel):
    observation_id: str = Field(min_length=1)
    execution_id: str = ""
    content: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: str = "UNKNOWN"


class InvestigationBudget(ContractModel):
    max_iterations: int = 12
    max_tool_calls: int = 40
    max_depth: int = 3
    max_agents: int = 6
    max_tokens: int = 200_000
    max_cost_usd: float = 0.0    # 0 = unlimited tracking only
    timeout_seconds: float = 600.0
    spent_iterations: int = 0
    spent_tool_calls: int = 0
    spent_tokens: int = 0
    spent_cost_usd: float = 0.0


class InvestigationPlan(ContractModel):
    plan_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    tasks: list[AgentTask] = Field(default_factory=list)
    budget: InvestigationBudget = Field(
        default_factory=InvestigationBudget)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class Hypothesis(ContractModel):
    hypothesis_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    status: str = "open"  # open|supported|refuted|dropped
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    confidence: str = "UNKNOWN"
    alternatives: list[str] = Field(default_factory=list)
    # causal safety: correlation must be labeled, never asserted as cause
    causal_claim: bool = False
    causal_label: str = "correlation"  # correlation|suspected_cause|proven


class InvestigationState(ContractModel):
    investigation_id: str = Field(min_length=1)
    state: AgentState = AgentState.CREATED
    plan: InvestigationPlan | None = None
    executions: list[AgentExecution] = Field(default_factory=list)
    decisions: list[AgentDecision] = Field(default_factory=list)
    observations: list[AgentObservation] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    tool_invocations: list[ToolInvocation] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    created_at: UTCDateTime | None = None
    updated_at: UTCDateTime | None = None
    limitations: list[str] = Field(default_factory=list)


class InvestigationReport(ContractModel):
    report_id: str = Field(min_length=1)
    investigation_id: str
    problem: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    agents_used: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    hypotheses_supported: list[Hypothesis] = Field(default_factory=list)
    hypotheses_refuted: list[Hypothesis] = Field(default_factory=list)
    conclusions: list[str] = Field(default_factory=list)
    recommendations: list[OptimizationRecommendation] = Field(
        default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0


class ModelRequest(ContractModel):
    model_id: str = ""
    system: str = ""
    prompt: str = ""
    max_tokens: int = 4096
    temperature: float = 0.0
    tools: list[dict[str, Any]] = Field(default_factory=list)


class ModelResponse(ContractModel):
    text: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    model_id: str = ""
    stop_reason: str = ""


class KnowledgeChunk(ContractModel):
    chunk_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    text: str = Field(min_length=1)
    kind: str = "doc"               # doc|evidence|rule|fixture
    provenance: str = ""
    tokens: int = 0
    metadata: dict[str, str] = Field(default_factory=dict)


class RetrievalResult(ContractModel):
    query: str
    chunks: list[KnowledgeChunk] = Field(default_factory=list)
    method: str = "lexical"
    limitations: list[str] = Field(default_factory=list)
