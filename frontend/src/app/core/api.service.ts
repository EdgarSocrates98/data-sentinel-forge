import { HttpClient, HttpParams } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { Observable } from "rxjs";

import { environment } from "../../environments/environment";
import {
  AgentDescriptor,
  AlertRecord,
  AnalyzeRequest,
  CapabilityDescriptor,
  CompareRequest,
  CompareResponse,
  ExecutionSnapshot,
  HealthResponse,
  InvestigationCreateRequest,
  InvestigationCreateResponse,
  InvestigationDetail,
  InvestigationSummary,
  PlanCreateRequest,
  PlanCreateResponse,
  PlanDryRunResult,
  PlanExecutionResult,
  PlanStateResponse,
  PlanSummary,
  RegressionFinding,
  RemediationPlan,
  SnapshotIngestResponse,
  ToolManifestEntry,
  WatchCreateRequest,
  WatchCreateResponse,
  WatchDeleteResponse,
  WatchRunAlert,
  WatchStateResponse,
  WatchSummary,
} from "./api.models";

/**
 * Typed client for the Sentinel Control Center API.
 * All endpoints are versioned under `environment.apiBaseUrl`
 * (default `http://127.0.0.1:8790/api/v1`).
 */
@Injectable({ providedIn: "root" })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  health(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.base}/health`);
  }

  capabilities(): Observable<CapabilityDescriptor[]> {
    return this.http.get<CapabilityDescriptor[]>(`${this.base}/capabilities`);
  }

  tools(): Observable<ToolManifestEntry[]> {
    return this.http.get<ToolManifestEntry[]>(`${this.base}/tools`);
  }

  agents(): Observable<AgentDescriptor[]> {
    return this.http.get<AgentDescriptor[]>(`${this.base}/agents`);
  }

  severities(): Observable<string[]> {
    return this.http.get<string[]>(`${this.base}/severities`);
  }

  createInvestigation(
    body: InvestigationCreateRequest,
  ): Observable<InvestigationCreateResponse> {
    return this.http.post<InvestigationCreateResponse>(
      `${this.base}/investigations`,
      { problem: body.problem, files: body.files ?? {} },
    );
  }

  listInvestigations(): Observable<InvestigationSummary[]> {
    return this.http.get<InvestigationSummary[]>(
      `${this.base}/investigations`,
    );
  }

  getInvestigation(id: string): Observable<InvestigationDetail> {
    return this.http.get<InvestigationDetail>(
      `${this.base}/investigations/${encodeURIComponent(id)}`,
    );
  }

  /**
   * SSE stream URL for live investigation events. Consumed with
   * `EventSource` (read-only GET stream, no request body).
   */
  investigationStreamUrl(id: string): string {
    return `${this.base}/investigations/${encodeURIComponent(id)}/stream`;
  }

  analyze(
    analyzerId: string,
    file: string,
  ): Observable<Record<string, unknown>> {
    const body: AnalyzeRequest = { file };
    return this.http.post<Record<string, unknown>>(
      `${this.base}/analyze/${encodeURIComponent(analyzerId)}`,
      body,
    );
  }

  /* ----------------------------------------------------------------
     Operational endpoints (Cycle 07 §3–§7). Snapshots are ingested
     observations; watches evaluate only via explicit POST /run;
     remediation executes allowlisted local actions only.
     ---------------------------------------------------------------- */

  /** POST /snapshots — ingest one real execution snapshot. */
  ingestSnapshot(
    body: ExecutionSnapshot,
  ): Observable<SnapshotIngestResponse> {
    return this.http.post<SnapshotIngestResponse>(
      `${this.base}/snapshots`,
      body,
    );
  }

  /**
   * GET /snapshots — snapshots sorted by `started_at` server-side.
   * Optional `platform`/`jobId` map to the query params.
   */
  listSnapshots(filter?: {
    platform?: string;
    jobId?: string;
  }): Observable<ExecutionSnapshot[]> {
    let params = new HttpParams();
    if (filter?.platform) params = params.set("platform", filter.platform);
    if (filter?.jobId) params = params.set("job_id", filter.jobId);
    return this.http.get<ExecutionSnapshot[]>(`${this.base}/snapshots`, {
      params,
    });
  }

  /** POST /history/compare — compare a snapshot to a baseline set. */
  compareSnapshots(body: CompareRequest): Observable<CompareResponse> {
    return this.http.post<CompareResponse>(
      `${this.base}/history/compare`,
      body,
    );
  }

  /**
   * GET /history/regressions — regression findings for `currentId`
   * evaluated against the full history of `jobId`.
   */
  listRegressions(
    jobId: string,
    currentId: string,
  ): Observable<RegressionFinding[]> {
    const params = new HttpParams()
      .set("job_id", jobId)
      .set("current_id", currentId);
    return this.http.get<RegressionFinding[]>(
      `${this.base}/history/regressions`,
      { params },
    );
  }

  /**
   * POST /watches — creates a DISABLED watch (§8.5: the API never
   * starts monitoring without an explicit action).
   */
  createWatch(body: WatchCreateRequest): Observable<WatchCreateResponse> {
    return this.http.post<WatchCreateResponse>(`${this.base}/watches`, body);
  }

  listWatches(): Observable<WatchSummary[]> {
    return this.http.get<WatchSummary[]>(`${this.base}/watches`);
  }

  /** POST /watches/{id}/run — single manual evaluation → alerts. */
  runWatch(id: string): Observable<WatchRunAlert[]> {
    return this.http.post<WatchRunAlert[]>(
      `${this.base}/watches/${encodeURIComponent(id)}/run`,
      {},
    );
  }

  pauseWatch(id: string): Observable<WatchStateResponse> {
    return this.http.post<WatchStateResponse>(
      `${this.base}/watches/${encodeURIComponent(id)}/pause`,
      {},
    );
  }

  resumeWatch(id: string): Observable<WatchStateResponse> {
    return this.http.post<WatchStateResponse>(
      `${this.base}/watches/${encodeURIComponent(id)}/resume`,
      {},
    );
  }

  deleteWatch(id: string): Observable<WatchDeleteResponse> {
    return this.http.post<WatchDeleteResponse>(
      `${this.base}/watches/${encodeURIComponent(id)}/delete`,
      {},
    );
  }

  /** GET /alerts — alert history emitted by the watch engine. */
  listAlerts(): Observable<AlertRecord[]> {
    return this.http.get<AlertRecord[]>(`${this.base}/alerts`);
  }

  /**
   * POST /remediation/plans — create a DRAFT plan from an
   * investigation finding (investigation_id + finding_id) or an
   * embedded finding payload.
   */
  createPlan(body: PlanCreateRequest): Observable<PlanCreateResponse> {
    return this.http.post<PlanCreateResponse>(
      `${this.base}/remediation/plans`,
      body,
    );
  }

  listPlans(): Observable<PlanSummary[]> {
    return this.http.get<PlanSummary[]>(`${this.base}/remediation/plans`);
  }

  getPlan(id: string): Observable<RemediationPlan> {
    return this.http.get<RemediationPlan>(
      `${this.base}/remediation/plans/${encodeURIComponent(id)}`,
    );
  }

  /** DRAFT/VALIDATED → AWAITING_APPROVAL. */
  submitPlan(id: string): Observable<PlanStateResponse> {
    return this.http.post<PlanStateResponse>(
      `${this.base}/remediation/plans/${encodeURIComponent(id)}/submit`,
      {},
    );
  }

  /** AWAITING_APPROVAL → APPROVED. Never anonymous, never executes. */
  approvePlan(id: string, approver: string): Observable<PlanStateResponse> {
    return this.http.post<PlanStateResponse>(
      `${this.base}/remediation/plans/${encodeURIComponent(id)}/approve`,
      { approver },
    );
  }

  rejectPlan(id: string, reason: string): Observable<PlanStateResponse> {
    return this.http.post<PlanStateResponse>(
      `${this.base}/remediation/plans/${encodeURIComponent(id)}/reject`,
      { reason },
    );
  }

  /** Structured preview — never applies anything (§7.4). */
  dryRunPlan(id: string): Observable<PlanDryRunResult> {
    return this.http.post<PlanDryRunResult>(
      `${this.base}/remediation/plans/${encodeURIComponent(id)}/dry-run`,
      {},
    );
  }

  /**
   * Local allowlisted execution — requires APPROVED. There is no
   * cloud execution in this API by design.
   */
  executeLocalPlan(id: string): Observable<PlanExecutionResult> {
    return this.http.post<PlanExecutionResult>(
      `${this.base}/remediation/plans/${encodeURIComponent(id)}/execute-local`,
      {},
    );
  }
}
