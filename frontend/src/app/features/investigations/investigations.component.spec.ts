import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";

import { environment } from "../../../environments/environment";
import { InvestigationsComponent } from "./investigations.component";

describe("InvestigationsComponent (list)", () => {
  let fixture: ComponentFixture<InvestigationsComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InvestigationsComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(InvestigationsComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function flushList(body: object[], status = 200): void {
    fixture.detectChanges();
    const req = http.expectOne(`${environment.apiBaseUrl}/investigations`);
    expect(req.request.method).toBe("GET");
    req.flush(body, { status, statusText: "" });
    fixture.detectChanges();
  }

  it("renders real investigations from the API", () => {
    flushList([
      {
        investigation_id: "inv-1",
        status: "completed",
        created: 1730000000,
      },
    ]);
    const el: HTMLElement = fixture.nativeElement;
    const rows = el.querySelectorAll(".inv-table tbody tr");
    expect(rows.length).toBe(1);
    expect(el.textContent).toContain("inv-1");
    expect(el.textContent).toContain("Concluída");
  });

  it("shows an honest empty state when the API returns nothing", () => {
    flushList([]);
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("Nenhuma investigação ainda");
    expect(el.querySelector(".inv-table")).toBeNull();
  });

  it("shows an error state with retry when the API is unreachable", () => {
    fixture.detectChanges();
    const req = http.expectOne(`${environment.apiBaseUrl}/investigations`);
    req.error(new ProgressEvent("error"), { status: 0 });
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("API indisponível");
    expect(el.querySelector("button.ds-btn")?.textContent).toContain(
      "Tentar novamente",
    );
  });
});
