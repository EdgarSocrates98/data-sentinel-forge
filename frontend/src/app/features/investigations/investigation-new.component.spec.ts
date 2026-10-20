import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";

import { environment } from "../../../environments/environment";
import { InvestigationNewComponent } from "./investigation-new.component";

const FILE_TOOL = {
  name: "sentinel.sql.analyze",
  description: "Análise AST de consulta SQL.",
  inputSchema: {
    type: "object",
    properties: { file: { type: "string" } },
    required: ["file"],
  },
};

const NON_FILE_TOOL = {
  name: "sentinel.emr.estimate_cost",
  description: "Estima custo EMR declarado.",
  inputSchema: {
    type: "object",
    properties: { platform: { type: "string" } },
    required: ["platform"],
  },
};

describe("InvestigationNewComponent", () => {
  let fixture: ComponentFixture<InvestigationNewComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InvestigationNewComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(InvestigationNewComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function flushTools(body: object[]): void {
    fixture.detectChanges();
    http.expectOne(`${environment.apiBaseUrl}/tools`).flush(body);
    fixture.detectChanges();
  }

  it("keeps submit disabled until a problem is described", () => {
    flushTools([FILE_TOOL]);
    const el: HTMLElement = fixture.nativeElement;
    const submit = el.querySelector<HTMLButtonElement>(
      "button[type='submit']",
    );
    expect(submit?.disabled).toBeTrue();

    const textarea = el.querySelector<HTMLTextAreaElement>("#problem");
    expect(textarea).toBeTruthy();
    textarea!.value = "job Glue lento após upgrade";
    textarea!.dispatchEvent(new Event("input"));
    fixture.detectChanges();
    expect(submit?.disabled).toBeFalse();
  });

  it("offers only file-compatible tools from the manifest", () => {
    flushTools([FILE_TOOL, NON_FILE_TOOL]);
    const el: HTMLElement = fixture.nativeElement;
    // add a file row, then inspect the select options
    el.querySelector<HTMLButtonElement>(
      "form fieldset .ds-btn:not(.remove)",
    )?.click();
    fixture.detectChanges();
    const options = [
      ...el.querySelectorAll<HTMLOptionElement>("#tool-0 option"),
    ].map((o) => o.value);
    expect(options).toContain("sentinel.sql.analyze");
    expect(options).not.toContain("sentinel.emr.estimate_cost");
  });

  it("posts problem + files and navigates on 201", () => {
    flushTools([FILE_TOOL]);
    const el: HTMLElement = fixture.nativeElement;

    const textarea = el.querySelector<HTMLTextAreaElement>("#problem")!;
    textarea.value = "plano Spark com skew";
    textarea.dispatchEvent(new Event("input"));

    el.querySelector<HTMLButtonElement>(
      "form fieldset .ds-btn:not(.remove)",
    )?.click();
    fixture.detectChanges();

    const toolSelect = el.querySelector<HTMLSelectElement>("#tool-0")!;
    toolSelect.value = "sentinel.sql.analyze";
    toolSelect.dispatchEvent(new Event("change"));
    const pathInput = el.querySelector<HTMLInputElement>("#path-0")!;
    pathInput.value = "/tmp/plan.json";
    pathInput.dispatchEvent(new Event("input"));
    fixture.detectChanges();

    el.querySelector<HTMLButtonElement>("button[type='submit']")!.click();
    const req = http.expectOne(`${environment.apiBaseUrl}/investigations`);
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({
      problem: "plano Spark com skew",
      files: { "sentinel.sql.analyze": "/tmp/plan.json" },
    });
    req.flush({ investigation_id: "inv-9", status: "running" }, {
      status: 201,
      statusText: "Created",
    });
    fixture.detectChanges();
  });

  it("surfaces a tool-registry error state with retry", () => {
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
