import { HttpClient } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { Observable } from "rxjs";

import { environment } from "../../environments/environment";
import {
  AgentDescriptor,
  AnalyzeRequest,
  CapabilityDescriptor,
  HealthResponse,
  InvestigationCreateRequest,
  InvestigationCreateResponse,
  InvestigationDetail,
  InvestigationSummary,
  ToolManifestEntry,
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
}
