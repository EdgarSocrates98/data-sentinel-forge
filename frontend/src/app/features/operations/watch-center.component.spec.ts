import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";

import { environment } from "../../../environments/environment";
import { WatchCenterComponent } from "./watch-center.component";

const WATCHES = [
  {
    watch_id: "w-1",
    workload: "glue-job-a",
    platform: "glue",
    rule: "regression",
    interval_s: 300,
    enabled: false,
    severity: "HIGH",
  },
];

function flushAll(http: HttpTestingController): void {
  http.expectOne(`${environment.apiBaseUrl}/watches`).flush(WATCHES);
  http.expectOne(`${environment.apiBaseUrl}/alerts`).flush([]);
}

describe("WatchCenterComponent", () => {
  let fixture: ComponentFixture<WatchCenterComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WatchCenterComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(WatchCenterComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it("lists real watches with per-row actions", () => {
    fixture.detectChanges();
    flushAll(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("w-1");
    expect(el.textContent).toContain("glue-job-a");
    // created disabled → resume action, not pause
    expect(el.textContent).toContain("Retomar");
    expect(el.textContent).toContain("Avaliar agora");
    expect(el.textContent).toContain("Excluir");
  });

  it("creates a disabled watch via POST /watches", () => {
    fixture.detectChanges();
    flushAll(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;

    const set = (id: string, v: string | number) => {
      const input = el.querySelector<
        HTMLInputElement | HTMLSelectElement
      >(id)!;
      input.value = String(v);
      input.dispatchEvent(new Event("input"));
      input.dispatchEvent(new Event("change"));
    };
    set("#watch-id", "w-new");
    set("#watch-workload", "glue-job-a");
    set("#watch-platform", "glue");
    set("#watch-metrics", "duration_s, retry_count");
    fixture.detectChanges();
    el.querySelector("form")!.dispatchEvent(new Event("submit"));

    const req = http.expectOne(`${environment.apiBaseUrl}/watches`);
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({
      watch_id: "w-new",
      workload: "glue-job-a",
      platform: "glue",
      source: "local",
      metrics: ["duration_s", "retry_count"],
      rule: "regression",
      interval_s: 300,
      severity: "MEDIUM",
    });
    req.flush({ watch_id: "w-new", enabled: false }, { status: 201, statusText: "" });
    fixture.detectChanges();
    expect(el.textContent).toContain("criado desabilitado");
    // list refresh after create
    http.expectOne(`${environment.apiBaseUrl}/watches`).flush(WATCHES);
    fixture.detectChanges();
  });

  it("runs a manual evaluation and renders emitted alerts", () => {
    fixture.detectChanges();
    flushAll(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;

    const runBtn = [...el.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Avaliar agora"),
    )!;
    runBtn.click();
    const req = http.expectOne(`${environment.apiBaseUrl}/watches/w-1/run`);
    expect(req.request.method).toBe("POST");
    req.flush([
      {
        alert_id: "alert-1",
        kind: "job_failure",
        severity: "HIGH",
        message: "glue-job-a falhou",
        recovered: false,
        findings: [],
      },
    ]);
    fixture.detectChanges();
    expect(el.textContent).toContain("glue-job-a falhou");
    // alerts list refreshes after emitted alerts
    http.expectOne(`${environment.apiBaseUrl}/alerts`).flush([]);
    fixture.detectChanges();
  });

  it("requires two steps to delete a watch", () => {
    fixture.detectChanges();
    flushAll(http);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;

    const del = [...el.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Excluir"),
    )!;
    del.click();
    fixture.detectChanges();
    // no HTTP call yet — confirmation first
    http.expectNone(`${environment.apiBaseUrl}/watches/w-1/delete`);
    const confirm = [...el.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Confirmar exclusão"),
    )!;
    confirm.click();
    const req = http.expectOne(
      `${environment.apiBaseUrl}/watches/w-1/delete`,
    );
    expect(req.request.method).toBe("POST");
    req.flush({ deleted: "w-1" });
    http.expectOne(`${environment.apiBaseUrl}/watches`).flush([]);
    fixture.detectChanges();
    // deleted watch is gone from the list
    expect(el.textContent).not.toContain("w-1");
  });

  it("shows an error state when the watch list fails", () => {
    fixture.detectChanges();
    http
      .expectOne(`${environment.apiBaseUrl}/watches`)
      .error(new ProgressEvent("error"), { status: 0 });
    http
      .expectOne(`${environment.apiBaseUrl}/alerts`)
      .error(new ProgressEvent("error"), { status: 0 });
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain(
      "Não foi possível carregar os dados operacionais.",
    );
  });
});
