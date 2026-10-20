import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";

import { environment } from "../../../environments/environment";
import type { InvestigationReport } from "../../core/api.models";
import { ReportsComponent } from "./reports.component";

const LIST = [
  { investigation_id: "inv-aaa", status: "completed", created: 100 },
  { investigation_id: "inv-bbb", status: "completed", created: 200 },
];

function report(id: string, findings: object[] = []): InvestigationReport {
  return {
    report_id: id,
    investigation_id: id,
    problem: `problem ${id}`,
    context: {},
    agents_used: [],
    tools_used: ["sentinel.spark.analyze_plan"],
    findings: findings as InvestigationReport["findings"],
    hypotheses_supported: [],
    hypotheses_refuted: [],
    conclusions: [`conclusion ${id}`],
    recommendations: [],
    evidence: [],
    limitations: [],
    tokens_used: 10,
    cost_usd: 0,
    duration_seconds: 1,
  };
}

const FINDING = {
  finding_id: "f-1",
  category: "c",
  severity: "HIGH",
  status: "CONFIRMED",
  explanation: "x",
  evidence_ids: [],
  alternatives: [],
  recommendations: [],
  validation_steps: [],
};

describe("ReportsComponent", () => {
  let fixture: ComponentFixture<ReportsComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReportsComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ReportsComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function flushList(body = LIST): void {
    fixture.detectChanges();
    http
      .expectOne(`${environment.apiBaseUrl}/investigations`)
      .flush(body);
    fixture.detectChanges();
  }

  it("lists real investigations with the honest session-history note", () => {
    flushList();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("inv-aaa");
    expect(el.textContent).toContain("inv-bbb");
    expect(el.textContent).toContain("Histórico da sessão atual");
  });

  it("filters the list client-side by investigation id", () => {
    flushList();
    const el: HTMLElement = fixture.nativeElement;
    const input = el.querySelector<HTMLInputElement>("#report-filter")!;
    input.value = "bbb";
    input.dispatchEvent(new Event("input"));
    fixture.detectChanges();
    const rows = el.querySelectorAll(".data-table tbody tr");
    expect(rows.length).toBe(1);
    // inv-aaa remains in the compare selects; only the table is filtered
    const tbody = el.querySelector(".data-table tbody")!;
    expect(tbody.textContent).toContain("inv-bbb");
    expect(tbody.textContent).not.toContain("inv-aaa");
  });

  it("exports the real report payload as JSON", () => {
    flushList();
    const el: HTMLElement = fixture.nativeElement;
    const createUrl = spyOn(URL, "createObjectURL").and.returnValue(
      "blob:fake",
    );
    spyOn(URL, "revokeObjectURL");
    const click = spyOn(HTMLAnchorElement.prototype, "click");

    const btn = el.querySelector<HTMLButtonElement>(".export-btn")!;
    btn.click();
    const req = http.expectOne(
      `${environment.apiBaseUrl}/investigations/inv-bbb`,
    );
    expect(req.request.method).toBe("GET");
    req.flush(report("inv-bbb"));
    fixture.detectChanges();

    expect(createUrl).toHaveBeenCalled();
    const blob = createUrl.calls.mostRecent().args[0] as Blob;
    expect(blob.type).toBe("application/json");
    expect(click).toHaveBeenCalled();
  });

  it("compares two reports side by side with real metrics", () => {
    flushList();
    const el: HTMLElement = fixture.nativeElement;

    const selA = el.querySelector<HTMLSelectElement>("#cmp-a")!;
    const selB = el.querySelector<HTMLSelectElement>("#cmp-b")!;
    selA.value = "inv-aaa";
    selA.dispatchEvent(new Event("change"));
    selB.value = "inv-bbb";
    selB.dispatchEvent(new Event("change"));
    fixture.detectChanges();

    http
      .expectOne(`${environment.apiBaseUrl}/investigations/inv-aaa`)
      .flush(report("inv-aaa", [FINDING]));
    http
      .expectOne(`${environment.apiBaseUrl}/investigations/inv-bbb`)
      .flush(report("inv-bbb"));
    fixture.detectChanges();

    const table = el.querySelector(".cmp-table");
    expect(table).toBeTruthy();
    expect(el.textContent).toContain("Findings (total)");
    expect(el.textContent).toContain("HIGH");
    // tool diff and conclusions columns
    expect(el.textContent).toContain("sentinel.spark.analyze_plan");
    expect(el.textContent).toContain("conclusion inv-aaa");
    expect(el.textContent).toContain("conclusion inv-bbb");
    // diff rows highlighted
    expect(
      el.querySelectorAll(".cmp-table tr.differs").length,
    ).toBeGreaterThan(0);
  });

  it("shows the honest need-two message with a single report", () => {
    flushList([LIST[0]]);
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain(
      "São necessárias pelo menos duas investigações",
    );
    expect(el.querySelector("#cmp-a")).toBeNull();
  });
});
