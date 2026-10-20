import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";

import { environment } from "../../../environments/environment";
import { RemediationWorkspaceComponent } from "./remediation-workspace.component";

const LIST = [
  {
    plan_id: "rp-1",
    title: "Manual remediation",
    type: "manual",
    state: "DRAFT",
    finding_ids: ["f-1"],
  },
];

const DETAIL = {
  plan_id: "rp-1",
  title: "Manual remediation",
  remediation_type: "manual",
  state: "DRAFT",
  finding_ids: ["f-1"],
  evidence_ids: [],
  proposed_changes: [
    {
      target: "job.glue-etl",
      change: "Reduce memory pressure",
      params: {},
      local_action: null,
    },
  ],
  preconditions: ["manual review"],
  risks: ["unknown blast radius"],
  expected_effects: ["manual verification"],
  validation_procedure: ["re-run workload"],
  rollback_proposal: "none",
  rollback_limitations: ["manual steps not auto-reversible"],
  required_permissions: [],
  approval_required: true,
  approved_by: null,
  created_at: "2026-05-19T12:00:00+00:00",
  expires_at: null,
  state_history: [
    {
      from: "",
      to: "DRAFT",
      note: "created",
      at: "2026-05-19T12:00:00+00:00",
    },
  ],
};

/** The component eagerly loads plans AND the investigation picker list. */
function flushInitial(
  http: HttpTestingController,
  body: readonly unknown[] = LIST,
): void {
  http
    .expectOne(`${environment.apiBaseUrl}/remediation/plans`)
    .flush(body as object[]);
  http.expectOne(`${environment.apiBaseUrl}/investigations`).flush([]);
}

function buttonWith(el: HTMLElement, label: string): HTMLButtonElement | undefined {
  return [...el.querySelectorAll("button")].find((b) =>
    b.textContent?.includes(label),
  ) as HTMLButtonElement | undefined;
}

describe("RemediationWorkspaceComponent", () => {
  let fixture: ComponentFixture<RemediationWorkspaceComponent>;
  let http: HttpTestingController;
  let el: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RemediationWorkspaceComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(RemediationWorkspaceComponent);
    http = TestBed.inject(HttpTestingController);
    el = fixture.nativeElement;
  });

  afterEach(() => http.verify());

  it("lists plans and loads full detail on open", () => {
    fixture.detectChanges();
    flushInitial(http);
    fixture.detectChanges();
    expect(el.textContent).toContain("rp-1");

    const open = [...el.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Abrir"),
    )!;
    open.click();
    const req = http.expectOne(`${environment.apiBaseUrl}/remediation/plans/rp-1`);
    req.flush(DETAIL);
    fixture.detectChanges();

    expect(el.textContent).toContain("job.glue-etl");
    expect(el.textContent).toContain("Reduce memory pressure");
    expect(el.textContent).toContain("unknown blast radius");
    // state-gated actions for DRAFT: submit + reject (+ harmless dry-run)
    expect(buttonWith(el, "Submeter para aprovação")).toBeTruthy();
    expect(buttonWith(el, "Rejeitar")).toBeTruthy();
    // execute-local is gated to APPROVED — never rendered for DRAFT
    expect(buttonWith(el, "Executar ações locais")).toBeUndefined();
    // no cloud-execution button exists; the note states it explicitly
    expect(el.textContent).toContain("Não existe botão de execução cloud");
  });

  it("creates a plan from a manual finding via POST /remediation/plans", () => {
    fixture.detectChanges();
    flushInitial(http);
    fixture.detectChanges();

    // switch to manual mode
    const radios = el.querySelectorAll<HTMLInputElement>(
      'input[type="radio"]',
    );
    radios[1].click(); // manual
    fixture.detectChanges();

    const set = (id: string, v: string) => {
      const input = el.querySelector<
        HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
      >(id)!;
      input.value = v;
      input.dispatchEvent(new Event("input"));
      input.dispatchEvent(new Event("change"));
    };
    set("#rem-title-manual", "Fix glue job");
    set("#rem-explanation", "Job timed out twice");
    set("#rem-category", "timeout");
    set("#rem-severity", "HIGH");
    set("#rem-status", "CONFIRMED");
    set("#rem-recs", "Increase timeout\nScale workers");
    fixture.detectChanges();

    el.querySelectorAll("form")[0].dispatchEvent(new Event("submit"));

    const req = http.expectOne(`${environment.apiBaseUrl}/remediation/plans`);
    expect(req.request.method).toBe("POST");
    expect(req.request.body.finding.explanation).toBe("Job timed out twice");
    expect(req.request.body.finding.recommendations).toEqual([
      "Increase timeout",
      "Scale workers",
    ]);
    expect(req.request.body.title).toBe("Fix glue job");
    req.flush({ plan_id: "rp-1", state: "DRAFT" });
    // plan list refreshes after a successful create
    http
      .expectOne(`${environment.apiBaseUrl}/remediation/plans`)
      .flush(LIST);
    fixture.detectChanges();
    expect(el.textContent).toContain("criado");
  });

  it("gates approval behind a named approver and never auto-executes", () => {
    fixture.detectChanges();
    flushInitial(http);
    fixture.detectChanges();
    const open = [...el.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Abrir"),
    )!;
    open.click();
    http
      .expectOne(`${environment.apiBaseUrl}/remediation/plans/rp-1`)
      .flush({ ...DETAIL, state: "AWAITING_APPROVAL" });
    fixture.detectChanges();

    // approve button disabled until approver name is set
    const approveBtn = [...el.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Aprovar"),
    )! as HTMLButtonElement;
    expect(approveBtn.disabled).toBe(true);

    const input = el.querySelector<HTMLInputElement>("#rem-approver")!;
    input.value = "edgar";
    input.dispatchEvent(new Event("input"));
    fixture.detectChanges();
    expect(approveBtn.disabled).toBe(false);
    approveBtn.click();

    const req = http.expectOne(
      `${environment.apiBaseUrl}/remediation/plans/rp-1/approve`,
    );
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({ approver: "edgar" });
    req.flush({ ...DETAIL, state: "APPROVED", approved_by: "edgar" });
    fixture.detectChanges();

    // after approval: refresh + dry-run + execute-local become available
    http
      .expectOne(`${environment.apiBaseUrl}/remediation/plans/rp-1`)
      .flush({ ...DETAIL, state: "APPROVED", approved_by: "edgar" });
    http.expectOne(`${environment.apiBaseUrl}/remediation/plans`).flush(LIST);
    fixture.detectChanges();
    expect(el.textContent).toContain("Dry-run");
    expect(el.textContent).toContain("Executar ações locais");
  });

  it("runs dry-run without applying changes", () => {
    fixture.detectChanges();
    flushInitial(http);
    fixture.detectChanges();
    const open = [...el.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Abrir"),
    )!;
    open.click();
    http
      .expectOne(`${environment.apiBaseUrl}/remediation/plans/rp-1`)
      .flush({ ...DETAIL, state: "APPROVED", approved_by: "edgar" });
    fixture.detectChanges();

    const dryRun = [...el.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Dry-run"),
    )!;
    dryRun.click();
    const req = http.expectOne(
      `${environment.apiBaseUrl}/remediation/plans/rp-1/dry-run`,
    );
    expect(req.request.method).toBe("POST");
    req.flush({
      plan_id: "rp-1",
      state: "APPROVED",
      would_change: [
        {
          target: "job.glue-etl",
          change: "Reduce memory pressure",
          params: {},
          executable_locally: false,
          requires: "manual",
        },
      ],
      preconditions: ["manual review"],
      risks: [],
      rollback: "none",
      note: "manual steps require operator",
    });
    fixture.detectChanges();
    expect(el.textContent).toContain("nada foi aplicado");
    expect(el.textContent).toContain("manual steps require operator");
  });

  it("shows an error state when the plan list fails", () => {
    fixture.detectChanges();
    http
      .expectOne(`${environment.apiBaseUrl}/remediation/plans`)
      .error(new ProgressEvent("error"), { status: 0 });
    http.expectOne(`${environment.apiBaseUrl}/investigations`).flush([]);
    fixture.detectChanges();
    expect(el.textContent).toContain(
      "Não foi possível carregar os dados operacionais.",
    );
  });
});
