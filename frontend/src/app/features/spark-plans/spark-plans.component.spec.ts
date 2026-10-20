import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";

import { environment } from "../../../environments/environment";
import {
  SparkPlansComponent,
  extractPlanTree,
} from "./spark-plans.component";

const FILE_SCHEMA = {
  type: "object",
  properties: { file: { type: "string" } },
  required: ["file"],
};

const TOOLS = [
  {
    name: "sentinel.spark.analyze_plan",
    description: "Analisa plano físico Spark.",
    inputSchema: FILE_SCHEMA,
  },
  {
    name: "sentinel.spark.optimize",
    description: "Recomendações de otimização.",
    inputSchema: FILE_SCHEMA,
  },
];

const PAYLOAD = {
  report_id: "rep-1",
  findings: [
    {
      finding_id: "f-1",
      category: "large_shuffle",
      severity: "MEDIUM",
      status: "PROBABLE",
      explanation: "exchange sem broadcast",
      evidence_ids: [],
      alternatives: [],
      recommendations: [],
      validation_steps: [],
    },
  ],
  summary: "1 achado(s): PROBABLE=1",
  limitations: [],
};

function setup(http: HttpTestingController): void {
  http.expectOne(`${environment.apiBaseUrl}/tools`).flush(TOOLS);
}

describe("SparkPlansComponent", () => {
  let fixture: ComponentFixture<SparkPlansComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SparkPlansComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(SparkPlansComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it("shows the honest empty state before any analysis", () => {
    fixture.detectChanges();
    setup(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("Nenhum plano analisado ainda");
    expect(el.querySelector("table")).toBeNull();
  });

  it("posts the file to analyze_plan and renders real findings", () => {
    fixture.detectChanges();
    setup(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;

    const file = el.querySelector<HTMLInputElement>("#sp-file")!;
    file.value = "/plans/explain.txt";
    file.dispatchEvent(new Event("input"));
    fixture.detectChanges();
    el.querySelector("form")!.dispatchEvent(new Event("submit"));
    fixture.detectChanges();

    const req = http.expectOne(
      `${environment.apiBaseUrl}/analyze/spark.analyze_plan`,
    );
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({ file: "/plans/explain.txt" });
    req.flush(PAYLOAD);
    fixture.detectChanges();

    expect(el.textContent).toContain("exchange sem broadcast");
    expect(el.textContent).toContain("MEDIUM");
    expect(el.querySelector(".data-table")).toBeTruthy();
  });

  it("renders a structured plan tree when the payload carries one", () => {
    fixture.detectChanges();
    setup(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;

    const file = el.querySelector<HTMLInputElement>("#sp-file")!;
    file.value = "/plans/tree.json";
    file.dispatchEvent(new Event("input"));
    fixture.detectChanges();
    el.querySelector("form")!.dispatchEvent(new Event("submit"));
    fixture.detectChanges();

    http.expectOne(`${environment.apiBaseUrl}/analyze/spark.analyze_plan`).flush(
      {
        ...PAYLOAD,
        stages: [
          {
            name: "Stage 0",
            children: [{ name: "Scan parquet" }, { name: "Exchange" }],
          },
        ],
      },
    );
    fixture.detectChanges();

    const tree = el.querySelector(".plan-tree");
    expect(tree).toBeTruthy();
    expect(el.textContent).toContain("Stage 0");
    expect(el.textContent).toContain("Scan parquet");
  });

  it("extractPlanTree returns null when no tree exists (honest path)", () => {
    fixture.detectChanges();
    setup(http); // the constructor load still needs a response
    expect(extractPlanTree(PAYLOAD)).toBeNull();
    expect(extractPlanTree({})).toBeNull();
    expect(
      extractPlanTree({ stages: [{ name: "s1" }] }),
    ).toEqual({
      kind: "nodes",
      nodes: [{ label: "s1", children: [] }],
    });
  });

  it("shows an error alert when the analysis fails", () => {
    fixture.detectChanges();
    setup(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;

    const file = el.querySelector<HTMLInputElement>("#sp-file")!;
    file.value = "/plans/bad.txt";
    file.dispatchEvent(new Event("input"));
    fixture.detectChanges();
    el.querySelector("form")!.dispatchEvent(new Event("submit"));
    fixture.detectChanges();

    http
      .expectOne(`${environment.apiBaseUrl}/analyze/spark.analyze_plan`)
      .flush({ detail: "file not found" }, { status: 404, statusText: "" });
    fixture.detectChanges();

    expect(el.textContent).toContain("A análise do plano falhou.");
    expect(el.textContent).toContain("file not found");
    expect(el.querySelector("table")).toBeNull();
  });
});
