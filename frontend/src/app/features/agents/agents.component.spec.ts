import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";

import { environment } from "../../../environments/environment";
import type { AgentDescriptor } from "../../core/api.models";
import { AgentsComponent } from "./agents.component";

function agent(id: string): AgentDescriptor {
  return {
    agent_id: id,
    name: `${id} name`,
    responsibility: `${id} responsibility`,
    capabilities: [],
    allowed_tools: [`sentinel.${id}.tool`],
    input_schema: {},
    output_schema: {},
    policy: "deterministic_first",
    max_iterations: 8,
    max_tool_calls: 20,
    model_profile: "offline",
    version: "1.0.0",
  };
}

const AGENTS = [
  agent("coordinator"),
  agent("spark-expert"),
  agent("emr-ec2-expert"),
];

const REPORT = {
  report_id: "inv-1",
  investigation_id: "inv-1",
  problem: "slow job",
  context: {},
  agents_used: ["spark-expert", "coordinator"],
  tools_used: ["sentinel.spark.analyze_plan"],
  findings: [],
  hypotheses_supported: [],
  hypotheses_refuted: [],
  conclusions: [],
  recommendations: [],
  evidence: [],
  limitations: [],
  tokens_used: 1234,
  cost_usd: 0,
  duration_seconds: 4.2,
};

describe("AgentsComponent", () => {
  let fixture: ComponentFixture<AgentsComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AgentsComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(AgentsComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function flushAll(
    investigations = [{ investigation_id: "inv-1", status: "completed", created: 1 }],
  ): void {
    fixture.detectChanges();
    http.expectOne(`${environment.apiBaseUrl}/agents`).flush(AGENTS);
    http.expectOne(`${environment.apiBaseUrl}/tools`).flush([]);
    http.expectOne(`${environment.apiBaseUrl}/investigations`).flush(
      investigations,
    );
    fixture.detectChanges();
  }

  it("renders the real specialist registry table", () => {
    flushAll();
    const el: HTMLElement = fixture.nativeElement;
    const rows = el.querySelectorAll(".data-table tbody tr");
    expect(rows.length).toBe(3);
    expect(el.textContent).toContain("spark-expert");
    expect(el.textContent).toContain("sentinel.spark-expert.tool");
    expect(el.textContent).toContain("deterministic_first");
    expect(el.textContent).toContain("offline");
  });

  it("shows real per-investigation agent/tool/token activity", () => {
    flushAll();
    const el: HTMLElement = fixture.nativeElement;

    const select = el.querySelector<HTMLSelectElement>("#inv-select")!;
    select.value = "inv-1";
    select.dispatchEvent(new Event("change"));
    fixture.detectChanges();

    http
      .expectOne(`${environment.apiBaseUrl}/investigations/inv-1`)
      .flush(REPORT);
    fixture.detectChanges();

    // tokens reported verbatim — no gauge
    expect(el.textContent).toContain("1234");
    expect(el.textContent).toContain("spark-expert");
    expect(el.textContent).toContain("sentinel.spark.analyze_plan");
  });

  it("shows the honest empty state when no investigations exist", () => {
    flushAll([]);
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain(
      "Nenhuma investigação concluída nesta sessão",
    );
    expect(el.querySelector("#inv-select")).toBeNull();
  });

  it("shows an error state with retry when the API is unreachable", () => {
    fixture.detectChanges();
    // forkJoin cancels siblings once one request fails — error whatever
    // is still open without touching cancelled requests.
    for (const req of http.match(() => true)) {
      if (!req.cancelled) {
        req.error(new ProgressEvent("error"), { status: 0 });
      }
    }
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("API indisponível");
    expect(el.textContent).toContain("Tentar novamente");
  });
});
