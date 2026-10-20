import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";

import { environment } from "../../../environments/environment";
import { WorkloadsComponent } from "./workloads.component";

const FILE_SCHEMA = {
  type: "object",
  properties: { file: { type: "string" } },
  required: ["file"],
};

const TOOLS = [
  {
    name: "sentinel.glue.diagnose_run",
    description: "Diagnostica um run Glue.",
    inputSchema: FILE_SCHEMA,
  },
  {
    name: "sentinel.emr.analyze_ec2",
    description: "Diagnostica EMR on EC2.",
    inputSchema: FILE_SCHEMA,
  },
  {
    name: "sentinel.emr.analyze_serverless",
    description: "Diagnostica EMR Serverless.",
    inputSchema: FILE_SCHEMA,
  },
  {
    name: "sentinel.emr.analyze_eks",
    description: "Diagnostica EMR on EKS.",
    inputSchema: FILE_SCHEMA,
  },
  {
    name: "sentinel.emr.estimate_cost",
    description: "Estima custo EMR.",
    inputSchema: {
      type: "object",
      properties: { platform: { type: "string" } },
      required: ["platform"],
    },
  },
  {
    name: "sentinel.quality.detect_drift",
    description: "Drift.",
    inputSchema: {
      type: "object",
      properties: {
        baseline_file: { type: "string" },
        current_file: { type: "string" },
      },
      required: ["baseline_file", "current_file"],
    },
  },
];

const FINDINGS_PAYLOAD = {
  report_id: "rep-1",
  findings: [
    {
      finding_id: "f-1",
      category: "timeout",
      severity: "HIGH",
      status: "CONFIRMED",
      explanation: "driver timeout",
      evidence_ids: ["e-1"],
      alternatives: [],
      recommendations: ["aumentar timeout"],
      validation_steps: [],
    },
  ],
  summary: "1 achado(s): CONFIRMED=1",
  limitations: ["saída truncada"],
};

function flushTools(http: HttpTestingController): void {
  http.expectOne(`${environment.apiBaseUrl}/tools`).flush(TOOLS);
}

describe("WorkloadsComponent", () => {
  let fixture: ComponentFixture<WorkloadsComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WorkloadsComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(WorkloadsComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it("lists only file-compatible workload tools and hides non-file tools", () => {
    fixture.detectChanges();
    flushTools(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    const options = [...el.querySelectorAll("#wl-tool option")].map((o) =>
      o.textContent?.trim(),
    );
    expect(options).toContain("sentinel.glue.diagnose_run");
    expect(options).toContain("sentinel.emr.analyze_ec2");
    // detect_drift requires two files — not callable via {file}
    expect(options).not.toContain("sentinel.quality.detect_drift");
  });

  it("shows an honest note for EMR cost estimation with required inputs", () => {
    fixture.detectChanges();
    flushTools(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("Estimativa de custo EMR");
    expect(el.textContent).toContain("sentinel.emr.estimate_cost");
    // the missing required input is surfaced verbatim from the manifest
    expect(el.textContent).toContain("platform");
    // no form is rendered for the cost tool
    expect(el.querySelector('input[formControlName="vcpu_hours"]')).toBeNull();
  });

  it("runs the EMR platform analyzer and renders real findings", () => {
    fixture.detectChanges();
    flushTools(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;

    const file = el.querySelector<HTMLInputElement>("#emr-file")!;
    file.value = "/data/emr.json";
    file.dispatchEvent(new Event("input"));
    fixture.detectChanges();

    const form = el.querySelectorAll("form")[1];
    form.dispatchEvent(new Event("submit"));
    fixture.detectChanges();

    const req = http.expectOne(
      `${environment.apiBaseUrl}/analyze/emr.analyze_ec2`,
    );
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({ file: "/data/emr.json" });
    req.flush({
      analyzer: "emr.ec2",
      findings: FINDINGS_PAYLOAD.findings,
      limitations: FINDINGS_PAYLOAD.limitations,
    });
    fixture.detectChanges();

    expect(el.textContent).toContain("driver timeout");
    expect(el.textContent).toContain("HIGH");
    expect(el.textContent).toContain("saída truncada");
  });

  it("builds a descriptive differences table from two session results", () => {
    fixture.detectChanges();
    flushTools(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;

    // run the same analysis twice via the generic form
    const tool = el.querySelector<HTMLSelectElement>("#wl-tool")!;
    tool.value = "sentinel.glue.diagnose_run";
    tool.dispatchEvent(new Event("change"));
    const file = el.querySelector<HTMLInputElement>("#wl-file")!;
    file.value = "/data/a.json";
    file.dispatchEvent(new Event("input"));
    fixture.detectChanges();
    el.querySelectorAll("form")[0].dispatchEvent(new Event("submit"));
    http
      .expectOne(`${environment.apiBaseUrl}/analyze/glue.diagnose_run`)
      .flush(FINDINGS_PAYLOAD);
    fixture.detectChanges();

    file.value = "/data/b.json";
    file.dispatchEvent(new Event("input"));
    fixture.detectChanges();
    el.querySelectorAll("form")[0].dispatchEvent(new Event("submit"));
    http
      .expectOne(`${environment.apiBaseUrl}/analyze/glue.diagnose_run`)
      .flush({ ...FINDINGS_PAYLOAD, findings: [] });
    fixture.detectChanges();

    const checks = el.querySelectorAll<HTMLInputElement>(
      ".compare-check input",
    );
    expect(checks.length).toBe(2);
    checks[0].click();
    checks[1].click();
    fixture.detectChanges();

    const table = el.querySelector(".compare-table");
    expect(table).toBeTruthy();
    expect(el.textContent).toContain("Findings (total)");
    // differing rows are highlighted
    expect(el.querySelectorAll(".compare-table tr.differs").length)
      .toBeGreaterThan(0);
    // never declares a winner
    expect(el.textContent).not.toContain("melhor");
  });

  it("shows an error state with retry when the registry is unreachable", () => {
    fixture.detectChanges();
    http
      .expectOne(`${environment.apiBaseUrl}/tools`)
      .error(new ProgressEvent("error"), { status: 0 });
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain(
      "Não foi possível carregar o registro de ferramentas.",
    );
  });
});
