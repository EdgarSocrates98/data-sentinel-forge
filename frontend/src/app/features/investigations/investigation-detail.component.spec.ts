import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import {
  ActivatedRoute,
  convertToParamMap,
  provideRouter,
} from "@angular/router";
import { of } from "rxjs";

import { environment } from "../../../environments/environment";
import type { InvestigationReport } from "../../core/api.models";
import { InvestigationDetailComponent } from "./investigation-detail.component";

const REPORT: InvestigationReport = {
  report_id: "inv-1",
  investigation_id: "inv-1",
  problem: "job Glue falhando",
  context: {
    tool_calls: [
      { tool_id: "sentinel.glue.diagnose_run", ok: true, duration_ms: 12.5 },
    ],
    validation: { checked: 1, errors: [], warnings: [] },
  },
  agents_used: ["sentinel.glue-doctor"],
  tools_used: ["sentinel.glue.diagnose_run"],
  findings: [
    {
      finding_id: "f-1",
      category: "out_of_memory",
      severity: "CRITICAL",
      status: "CONFIRMED",
      explanation: "Executor OOM no stage 3",
      evidence_ids: ["ev-1"],
      alternatives: [],
      recommendations: ["aumentar executor memory"],
      validation_steps: [],
    },
  ],
  hypotheses_supported: [
    {
      hypothesis_id: "rca:out_of_memory",
      statement: "causa-raiz provável em 'out_of_memory'",
      status: "supported",
      supporting_evidence: ["ev-1"],
      contradicting_evidence: [],
      confidence: "CONFIRMED",
      alternatives: [],
      causal_claim: false,
      causal_label: "suspected_cause",
    },
  ],
  hypotheses_refuted: [],
  conclusions: ["causa-raiz provável: OOM"],
  recommendations: [
    {
      recommendation_id: "r-1",
      target: "glue job",
      proposed_change: "aumentar memória",
      rationale: "OOM observado",
      expected_effect: "run estável",
      estimated_risk: "baixo",
      validation_plan: null,
      rollback_plan: null,
      evidence_ids: ["ev-1"],
    },
  ],
  evidence: [
    {
      evidence_id: "ev-1",
      source: "cloudwatch",
      source_location: "/aws/glue/jobs/output",
      captured_at: "2025-10-27T10:00:00Z",
      content_hash: "abc123",
      sanitized_excerpt: "java.lang.OutOfMemoryError",
      provenance: "observed",
      confidence: 0.9,
      access_metadata: null,
    },
  ],
  limitations: ["contexto parcial"],
  tokens_used: 0,
  cost_usd: 0,
  duration_seconds: 3.2,
};

describe("InvestigationDetailComponent", () => {
  let fixture: ComponentFixture<InvestigationDetailComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InvestigationDetailComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of(convertToParamMap({ id: "inv-1" })),
            snapshot: { queryParamMap: convertToParamMap({}) },
          },
        },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(InvestigationDetailComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it("renders the real report panels (findings, hypotheses, evidence, recs)", () => {
    fixture.detectChanges();
    http
      .expectOne(`${environment.apiBaseUrl}/investigations/inv-1`)
      .flush(REPORT);
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("Executor OOM no stage 3");
    expect(el.textContent).toContain("CRITICAL");
    expect(el.textContent).toContain("rca:out_of_memory");
    expect(el.textContent).toContain("suspected_cause");
    expect(el.textContent).toContain("java.lang.OutOfMemoryError");
    expect(el.textContent).toContain("aumentar memória");
    expect(el.textContent).toContain("contexto parcial");
    // severity badge uses the token-backed modifier class
    expect(el.querySelector(".ds-badge--severity-CRITICAL")).toBeTruthy();
  });

  it("shows not-found state on 404", () => {
    fixture.detectChanges();
    http
      .expectOne(`${environment.apiBaseUrl}/investigations/inv-1`)
      .flush(
        { detail: "investigation not found" },
        { status: 404, statusText: "Not Found" },
      );
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("Investigação não encontrada");
  });
});
