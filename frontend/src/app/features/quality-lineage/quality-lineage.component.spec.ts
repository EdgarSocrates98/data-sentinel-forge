import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";

import { environment } from "../../../environments/environment";
import { QualityLineageComponent } from "./quality-lineage.component";

const FILE_SCHEMA = {
  type: "object",
  properties: { file: { type: "string" } },
  required: ["file"],
};

const TOOLS = [
  {
    name: "sentinel.quality.assess",
    description: "Normaliza resultados exportados de qualidade.",
    inputSchema: {
      type: "object",
      properties: { file: { type: "string" }, adapter: { type: "string" } },
      required: ["file"],
    },
  },
  {
    name: "sentinel.quality.detect_drift",
    description: "Drift entre amostras.",
    inputSchema: {
      type: "object",
      properties: {
        baseline_file: { type: "string" },
        current_file: { type: "string" },
      },
      required: ["baseline_file", "current_file"],
    },
  },
  {
    name: "sentinel.lineage.ingest",
    description: "Ingere eventos OpenLineage.",
    inputSchema: FILE_SCHEMA,
  },
  {
    name: "sentinel.lineage.impact",
    description: "Impacto potencial.",
    inputSchema: {
      type: "object",
      properties: {
        file: { type: "string" },
        target: { type: "string" },
      },
      required: ["file", "target"],
    },
  },
];

const QUALITY_PAYLOAD = {
  observations: [
    {
      observation_id: "obs-1",
      rule_id: "r-completeness",
      dataset: { namespace: "s3://lake", name: "raw/events" },
      run_id: "run-9",
      timestamp: "2026-01-01T00:00:00Z",
      observed_value: 0.82,
      expected_value: 1.0,
      status: "FAIL",
      source: "great_expectations",
      metric_name: "completeness",
      unit: "ratio",
      provenance: "ge_result.json",
      limitations: [],
    },
  ],
  count: 1,
};

const LINEAGE_PAYLOAD = {
  events: 3,
  kind: "observed",
  downstream: {
    "s3://raw/events": ["s3://curated/customer_events"],
    "s3://curated/customer_events": ["s3://marts/daily_revenue"],
  },
  limitations: ["grafo parcial"],
};

describe("QualityLineageComponent", () => {
  let fixture: ComponentFixture<QualityLineageComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [QualityLineageComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(QualityLineageComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function flushTools(): void {
    http.expectOne(`${environment.apiBaseUrl}/tools`).flush(TOOLS);
    fixture.detectChanges();
  }

  it("renders real quality observations from assess", () => {
    fixture.detectChanges();
    flushTools();
    const el: HTMLElement = fixture.nativeElement;

    const file = el.querySelector<HTMLInputElement>("#q-file")!;
    file.value = "/data/ge_result.json";
    file.dispatchEvent(new Event("input"));
    fixture.detectChanges();
    el.querySelector("form")!.dispatchEvent(new Event("submit"));
    fixture.detectChanges();

    const req = http.expectOne(
      `${environment.apiBaseUrl}/analyze/quality.assess`,
    );
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({ file: "/data/ge_result.json" });
    req.flush(QUALITY_PAYLOAD);
    fixture.detectChanges();

    expect(el.textContent).toContain("completeness");
    expect(el.textContent).toContain("s3://lake/raw/events");
    expect(el.textContent).toContain("FAIL");
    expect(el.textContent).toContain("great_expectations");
  });

  it("declares drift unavailable with its real required inputs", () => {
    fixture.detectChanges();
    flushTools();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("Drift (baseline × atual)");
    expect(el.textContent).toContain("sentinel.quality.detect_drift");
    // no fake two-file form exists
    expect(el.querySelector('input[formControlName="baseline_file"]'))
      .toBeNull();
    expect(el.querySelector('input[formControlName="current_file"]'))
      .toBeNull();
  });

  it("renders lineage nodes and edges from a real ingest payload", () => {
    fixture.detectChanges();
    flushTools();
    const el: HTMLElement = fixture.nativeElement;

    el.querySelector<HTMLButtonElement>("#tab-lineage")!.click();
    fixture.detectChanges();

    const file = el.querySelector<HTMLInputElement>("#l-file")!;
    file.value = "/data/ol.jsonl";
    file.dispatchEvent(new Event("input"));
    fixture.detectChanges();
    // both tab panels coexist ([hidden]); submit the lineage one
    el.querySelector("#panel-lineage form")!.dispatchEvent(
      new Event("submit"),
    );
    fixture.detectChanges();

    http
      .expectOne(`${environment.apiBaseUrl}/analyze/lineage.ingest`)
      .flush(LINEAGE_PAYLOAD);
    fixture.detectChanges();

    // stats from the real payload
    expect(el.textContent).toContain("observed");
    // nodes + edges tables render the adjacency
    const edgeCells = [...el.querySelectorAll(".data-table td code")].map(
      (c) => c.textContent?.trim(),
    );
    expect(edgeCells).toContain("s3://raw/events");
    expect(edgeCells).toContain("s3://curated/customer_events");
    expect(edgeCells).toContain("s3://marts/daily_revenue");
    expect(el.textContent).toContain("grafo parcial");
    // impact honest note
    expect(el.textContent).toContain("sentinel.lineage.impact");
  });

  it("shows API-down state with retry", () => {
    fixture.detectChanges();
    http
      .expectOne(`${environment.apiBaseUrl}/tools`)
      .error(new ProgressEvent("error"), { status: 0 });
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("API indisponível");
  });
});
