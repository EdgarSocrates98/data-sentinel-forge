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
  created: number | null;
}

export type Severity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface Evidence {
  evidence_id: string;
  source: string;
  source_location: string;
  captured_at: string;
  content_hash: string;
  sanitized_excerpt: string;
  provenance: Record<string, unknown>;
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
  status: string;
  supporting_evidence: string[];
  contradicting_evidence: string[];
  confidence: string;
  alternatives: string[];
  causal_claim: boolean;
  causal_label: string;
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
  recommendations: Record<string, unknown>[];
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

/** POST /api/v1/analyze/{analyzer_id} — request body. */
export interface AnalyzeRequest {
  file: string;
}

/** SSE event emitted by /api/v1/investigations/{id}/stream. */
export interface InvestigationStreamEvent {
  event:
    | "INVESTIGATION_STARTED"
    | "TOOL_COMPLETED"
    | "HYPOTHESIS_CREATED"
    | "INVESTIGATION_COMPLETED"
    | "INVESTIGATION_FAILED"
    | string;
  data: Record<string, unknown>;
  ts: number;
}

/** Normalized API error produced by the error interceptor. */
export interface ApiError {
  status: number;
  message: string;
  detail: string | null;
  url: string;
}
