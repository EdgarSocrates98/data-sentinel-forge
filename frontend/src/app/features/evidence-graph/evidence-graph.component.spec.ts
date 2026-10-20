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

import { environment } from "../../../environments/environment";
import type { InvestigationReport } from "../../core/api.models";
import { EvidenceGraphComponent } from "./evidence-graph.component";

const REPORT: InvestigationReport = {
  report_id: "inv-1",
  investigation_id: "inv-1",
  problem: "skew no job",
  context: {},
  agents_used: [],
  tools_used: ["sentinel.spark.analyze_plan"],
  findings: [
    {
      finding_id: "f-1",
      category: "data_skew",
      severity: "HIGH",
      status: "PROBABLE",
      explanation: "stage 3 skew",
      evidence_ids: ["e-1"],
      alternatives: [],
      recommendations: [],
      validation_steps: [],
    },
  ],
  hypotheses_supported: [
    {
      hypothesis_id: "rca:data_skew",
      statement: "causa-raiz provável em 'data_skew'",
      status: "supported",
      supporting_evidence: ["e-1"],
      contradicting_evidence: [],
      confidence: "PROBABLE",
      alternatives: [],
      causal_claim: false,
      causal_label: "suspected_cause",
    },
  ],
  hypotheses_refuted: [],
  conclusions: [],
  recommendations: [],
  evidence: [],
  limitations: [],
  tokens_used: 0,
  cost_usd: 0,
  duration_seconds: 1,
};

describe("EvidenceGraphComponent", () => {
  let fixture: ComponentFixture<EvidenceGraphComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EvidenceGraphComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
          },
        },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(EvidenceGraphComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it("shows the investigation picker with real list data", () => {
    fixture.detectChanges();
    http
      .expectOne(`${environment.apiBaseUrl}/investigations`)
      .flush([
        { investigation_id: "inv-1", status: "completed", created: 1 },
      ]);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    const options = [...el.querySelectorAll("select option")].map(
      (o) => o.textContent?.trim(),
    );
    expect(options).toContain("inv-1");
  });

  it("renders graph + accessible tables from a real report", () => {
    fixture.detectChanges();
    http
      .expectOne(`${environment.apiBaseUrl}/investigations`)
      .flush([
        { investigation_id: "inv-1", status: "completed", created: 1 },
      ]);
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const select = el.querySelector<HTMLSelectElement>("select")!;
    select.value = "inv-1";
    select.dispatchEvent(new Event("change"));
    fixture.detectChanges();

    http
      .expectOne(`${environment.apiBaseUrl}/investigations/inv-1`)
      .flush(REPORT);
    fixture.detectChanges();

    // SVG canvas rendered with node groups
    expect(el.querySelector("svg.canvas")).toBeTruthy();
    expect(el.querySelectorAll("g.node").length).toBeGreaterThanOrEqual(4);
    // textual equivalent: node + edge tables are visible
    const tables = el.querySelectorAll("table.data-table");
    expect(tables.length).toBe(2);
    expect(el.textContent).toContain("SUPPORTED_BY");
    expect(el.textContent).toContain("stage 3 skew");
    // referenced-only evidence is honestly declared as a limitation
    expect(el.textContent).toContain("Limitações do grafo");
  });
});
