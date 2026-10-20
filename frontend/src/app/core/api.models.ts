/**
 * Typed contracts for the Sentinel Control Center API (`/api/v1/*`).
 * Mirrors the payloads emitted by `src/data_sentinel/api/app.py` —
 * thin delegation over core contracts, so shapes follow the Python
 * Pydantic models (`model_dump(mode="json")`).
 */

/** GET /api/v1/health */
export interface HealthResponse {
  status: string;
  version: string;
  api: string;
}

/** GET /api/v1/capabilities — CapabilityDescriptor (core/contracts/interop.py). */
export interface CapabilityDescriptor {
  capability_id: string;
  provider: string;
  version: string;
  input_types: string[];
  output_types: string[];
  permissions: string[];
  limitations: string[];
}

/** GET /api/v1/tools — MCP-style manifest (tools/registry.py::to_mcp_manifest). */
export interface ToolManifestEntry {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

/** GET /api/v1/agents — AgentDescriptor (core/contracts/agent.py). */
export interface AgentDescriptor {
  agent_id: string;
  name: string;
  responsibility: string;
  capabilities: AgentCapability[];
  allowed_tools: string[];
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  policy: string;
  max_iterations: number;
  max_tool_calls: number;
  model_profile: string;
  version: string;
}

export interface AgentCapability {
  capability_id: string;
  description?: string;
  [key: string]: unknown;
}

/** POST /api/v1/investigations — request body. */
export interface InvestigationCreateRequest {
  problem: string;
  files?: Record<string, string>;
}

/** POST /api/v1/investigations — 201 response. */
export interface InvestigationCreateResponse {
  investigation_id: string;
  status: string;
}

/** GET /api/v1/investigations — list item. */
export interface InvestigationSummary {
  investigation_id: string;
  status: string;
  /** Epoch seconds (time.time()). */
  created: number | null;
  /** Epoch seconds — last state change recorded by the store. */
  updated: number | null;
  /** Problem statement recorded at creation. */
  problem: string;
}

export type Severity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface Evidence {
  evidence_id: string;
  source: string;
  source_location: string;
  /** ISO-8601 UTC timestamp. */
  captured_at: string;
  content_hash: string;
  sanitized_excerpt: string;
  /** EvidenceProvenance enum wire value (e.g. "observed"). */
  provenance: string;
  /** 0.0–1.0 */
  confidence: number;
  access_metadata: Record<string, unknown> | null;
}

export interface Finding {
  finding_id: string;
  category: string;
  severity: Severity;
  status: string;
  explanation: string;
  evidence_ids: string[];
  alternatives: string[];
  recommendations: string[];
  validation_steps: string[];
}

export interface Hypothesis {
  hypothesis_id: string;
  statement: string;
  /** open | supported | refuted | dropped */
  status: string;
  /** evidence_ids supporting this hypothesis (RCA clusters). */
  supporting_evidence: string[];
  contradicting_evidence: string[];
  /** CONFIRMED | PROBABLE | POSSIBLE | UNKNOWN */
  confidence: string;
  alternatives: string[];
  causal_claim: boolean;
  /** correlation | suspected_cause | proven */
  causal_label: string;
}

/** OptimizationRecommendation (core/contracts/entities.py). */
export interface OptimizationRecommendation {
  recommendation_id: string;
  target: string;
  proposed_change: string;
  rationale: string;
  expected_effect: string | null;
  estimated_risk: string | null;
  validation_plan: string | null;
  rollback_plan: string | null;
  evidence_ids: string[];
}

/** GET /api/v1/investigations/{id} — InvestigationReport dump. */
export interface InvestigationReport {
  report_id: string;
  investigation_id: string;
  problem: string;
  context: Record<string, unknown>;
  agents_used: string[];
  tools_used: string[];
  findings: Finding[];
  hypotheses_supported: Hypothesis[];
  hypotheses_refuted: Hypothesis[];
  conclusions: string[];
  recommendations: OptimizationRecommendation[];
  evidence: Evidence[];
  limitations: string[];
  tokens_used: number;
  cost_usd: number;
  duration_seconds: number;
}

/** GET /api/v1/investigations/{id} while still running. */
export interface InvestigationRunning {
  investigation_id: string;
  status: "running";
}

export type InvestigationDetail = InvestigationReport | InvestigationRunning;

/** Narrow an `InvestigationDetail` to a finished report. */
export function isInvestigationReport(
  detail: InvestigationDetail,
): detail is InvestigationReport {
  return "findings" in detail;
}

/** POST /api/v1/analyze/{analyzer_id} — request body. */
export interface AnalyzeRequest {
  file: string;
}

/* ---- Typed shapes inside analyze responses (per-tool payloads). ----
   The endpoint returns `dict[str, Any]`; these interfaces document the
   known per-tool shapes and are populated via defensive guards, never
   assumed. */

/** DatasetReference (core/contracts/quality.py). */
export interface DatasetRef {
  namespace: string;
  name: string;
  platform: string;
  catalog: string;
  account: string;
  region: string;
  version: string;
  identifier: string;
}

/** QualityObservation (core/contracts/quality.py). */
export interface QualityObservation {
  observation_id: string;
  rule_id: string;
  dataset: DatasetRef | null;
  run_id: string;
  /** ISO-8601 or null — may be absent on the wire. */
  timestamp: string | null;
  observed_value: unknown;
  expected_value: unknown;
  /** PASS | FAIL | WARN | UNKNOWN */
  status: string;
  source: string;
  metric_name: string;
  unit: string;
  provenance: string;
  limitations: string[];
}

/** Payload of `sentinel.quality.assess` through POST /analyze. */
export interface QualityAssessResult {
  observations: QualityObservation[];
  count: number;
}

/** Payload of `sentinel.lineage.ingest` through POST /analyze. */
export interface LineageIngestResult {
  events: number;
  /** observed | static */
  kind: string;
  /** dataset key ("namespace/name") → downstream dataset keys. */
  downstream: Record<string, string[]>;
  limitations: string[];
}

/**
 * One message received on the SSE stream
 * `GET /api/v1/investigations/{id}/stream`. The backend emits the event
 * name in the `event:` field and a JSON payload in `data:`; `ts` is
 * stamped client-side on receipt (the wire payload carries no clock).
 */
export interface InvestigationStreamEvent {
  event:
    | "INVESTIGATION_STARTED"
    | "TOOL_COMPLETED"
    | "HYPOTHESIS_CREATED"
    | "INVESTIGATION_COMPLETED"
    | "INVESTIGATION_FAILED"
    | "ERROR"
    | string;
  data: Record<string, unknown>;
  /** Client-side receipt timestamp (ms since epoch), 0 when unknown. */
  ts: number;
}

/** Normalized API error produced by the error interceptor. */
export interface ApiError {
  status: number;
  message: string;
  detail: string | null;
  url: string;
}

/* ==================================================================
   Operational endpoints (Cycle 07 §3–§7) — snapshots, history,
   watches, alerts, remediation plans. Mirrors
   `core/contracts/snapshot.py`, `history/regression.py`,
   `watch/engine.py` and `remediation/plans.py` wire shapes.
   ================================================================== */

/**
 * ExecutionSnapshot (core/contracts/snapshot.py) — point-in-time
 * observation of one workload execution. Snapshots are ingested via
 * POST /snapshots, never fabricated; `provenance` declares how the
 * data was obtained (e.g. "direct", "imported").
 */
export interface ExecutionSnapshot {
  snapshot_id: string;
  platform: string;
  job_id: string | null;
  run_id: string | null;
  runtime: string | null;
  /** ISO-8601 strings — the engine carries no wall-clock. */
  started_at: string | null;
  ended_at: string | null;
  duration_s: number | null;
  input_bytes: number | null;
  output_bytes: number | null;
  resource_metrics: Record<string, number>;
  /** null = unknown. */
  failure: boolean | null;
  config_fingerprint: string | null;
  dataset_refs: string[];
  cost_observations: Record<string, number>;
  provenance: string;
  limitations: string[];
}

/** POST /api/v1/snapshots — 201 response. */
export interface SnapshotIngestResponse {
  snapshot_id: string;
  provenance: string;
}

/** POST /api/v1/history/compare — request body (CompareBody). */
export type BaselineKind = "previous" | "median" | "reference";

export interface CompareRequest {
  snapshot_id: string;
  baseline: BaselineKind;
  /** Required when baseline === "reference" (matched on run_id). */
  reference_id?: string | null;
}

/**
 * One regression signal emitted by history.regression.detect_regressions
 * (§4). A regression is a labeled signal — `causal_label` is always
 * "suspected_cause", never a confirmed root cause.
 */
export interface RegressionFinding {
  metric: string;
  baseline: number;
  current_value: number;
  magnitude: number;
  magnitude_pct: number | null;
  method: string;
  z_score: number | null;
  rationale: string;
  provenance: string;
  limitations: string[];
  related_changes: unknown[];
  investigation_recommendation: string;
  /** e.g. "POSSIBLE" — findings are never CONFIRMED by the engine. */
  confidence: string;
  causal_label: string;
}

/**
 * POST /api/v1/history/compare — response. Success returns a full
 * ComparisonResult dump plus `baseline_snapshot_ids` and
 * `regression_findings`; when no baseline is eligible the backend
 * early-returns only `comparable`, `incomparability_reasons` and
 * `limitations` — hence every other field is optional on the wire.
 */
export interface CompareResponse {
  comparable: boolean;
  incomparability_reasons?: string[];
  duration_delta_s?: number | null;
  duration_delta_pct?: number | null;
  resource_deltas?: Record<string, number>;
  volume_delta_input?: number | null;
  volume_delta_output?: number | null;
  /** True = a new failure appeared vs the baseline. */
  failure_regression?: boolean | null;
  config_drift?: string[];
  quality_changes?: string[];
  cost_delta?: Record<string, number>;
  limitations?: string[];
  baseline_snapshot_ids?: string[];
  regression_findings?: RegressionFinding[];
}

/** POST /api/v1/watches — request body (WatchBody). */
export interface WatchCreateRequest {
  watch_id: string;
  workload: string;
  platform: string;
  /** Only "local" is accepted via the API — "aws" is rejected. */
  source: "local";
  metrics: string[];
  /** regression | failure | threshold */
  rule: string;
  /** Server enforces >= 30s. */
  interval_s: number;
  severity: Severity;
}

/** GET /api/v1/watches — list item. */
export interface WatchSummary {
  watch_id: string;
  workload: string;
  platform: string;
  rule: string;
  interval_s: number;
  /** Watches are created disabled; enabled only via explicit resume. */
  enabled: boolean;
  severity: string;
}

/** POST /api/v1/watches — 201 response. */
export interface WatchCreateResponse {
  watch_id: string;
  enabled: boolean;
}

/** POST /api/v1/watches/{id}/pause|resume — response. */
export interface WatchStateResponse {
  watch_id: string;
  enabled: boolean;
  note?: string;
}

/** POST /api/v1/watches/{id}/delete — response. */
export interface WatchDeleteResponse {
  deleted: string;
}

/**
 * POST /api/v1/watches/{id}/run — one alert emitted by that manual
 * evaluation (no `watch_id`/`ts` on this shape — see AlertRecord).
 */
export interface WatchRunAlert {
  alert_id: string;
  kind: string;
  severity: string;
  message: string;
  recovered: boolean;
  findings: Record<string, unknown>[];
}

/** GET /api/v1/alerts — alert-history item (§5.4). */
export interface AlertRecord {
  alert_id: string;
  watch_id: string;
  /** job_failure | sla_breach | duration_regression | ... | recovery */
  kind: string;
  severity: string;
  message: string;
  /** Epoch seconds. */
  ts: number;
  recovered: boolean;
}

/**
 * Embedded Finding payload for POST /remediation/plans (PlanBody).
 * `finding_id` is optional — the backend assigns one when absent.
 */
export interface FindingPayload {
  finding_id?: string;
  category: string;
  severity: string;
  status: string;
  explanation: string;
  evidence_ids?: string[];
  alternatives?: string[];
  recommendations?: string[];
  validation_steps?: string[];
}

/** POST /api/v1/remediation/plans — request body (PlanBody). */
export interface PlanCreateRequest {
  investigation_id?: string;
  finding_id?: string;
  title?: string;
  finding?: FindingPayload;
}

/** POST /api/v1/remediation/plans — 201 response. */
export interface PlanCreateResponse {
  plan_id: string;
  state: string;
}

/** GET /api/v1/remediation/plans — list item. */
export interface PlanSummary {
  plan_id: string;
  title: string;
  /** remediation_type wire value. */
  type: string;
  state: string;
  finding_ids: string[];
}

/** ProposedChange (remediation/plans.py). */
export interface ProposedChange {
  target: string;
  change: string;
  params: Record<string, unknown>;
  /** Only executable when on the LOCAL_ACTION_ALLOWLIST. */
  local_action: string | null;
}

/** One entry of RemediationPlan.state_history. */
export interface PlanStateChange {
  from: string;
  to: string;
  note: string;
  /** ISO-8601 timestamp. */
  at: string;
}

/**
 * GET /api/v1/remediation/plans/{id} — full RemediationPlan dump.
 * Lifecycle: DRAFT → VALIDATED → AWAITING_APPROVAL → APPROVED
 * (+ REJECTED / EXPIRED). Execution is local-only and allowlisted.
 */
export interface RemediationPlan {
  plan_id: string;
  title: string;
  remediation_type: string;
  finding_ids: string[];
  evidence_ids: string[];
  proposed_changes: ProposedChange[];
  preconditions: string[];
  risks: string[];
  expected_effects: string[];
  validation_procedure: string[];
  rollback_proposal: string | null;
  rollback_limitations: string[];
  required_permissions: string[];
  approval_required: boolean;
  state: string;
  state_history: PlanStateChange[];
  /** ISO-8601 datetimes. */
  created_at: string;
  expires_at: string | null;
  approved_by: string | null;
}

/** POST …/submit|approve|reject — response. */
export interface PlanStateResponse {
  plan_id: string;
  state: string;
  note?: string;
}

/** One change preview inside a dry-run result (§7.4). */
export interface DryRunChange {
  target: string;
  change: string;
  params: Record<string, unknown>;
  executable_locally: boolean;
  /** local_action name or "cloud/manual execution". */
  requires: string;
}

/** POST /api/v1/remediation/plans/{id}/dry-run — response. */
export interface PlanDryRunResult {
  plan_id: string;
  state: string;
  would_change: DryRunChange[];
  preconditions: string[];
  risks: string[];
  rollback: string | null;
  note: string;
}

/** One per-change outcome inside an execute-local result. */
export interface PlanExecutionResultItem {
  target: string;
  action?: string;
  /** APPLIED | PENDING | BLOCKED | SKIPPED */
  status: string;
  reason?: string;
  result?: unknown;
}

/** POST /api/v1/remediation/plans/{id}/execute-local — response. */
export interface PlanExecutionResult {
  plan_id: string;
  results: PlanExecutionResultItem[];
  note: string;
}
