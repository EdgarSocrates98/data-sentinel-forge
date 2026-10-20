import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import {
  ActivatedRoute,
  Router,
  convertToParamMap,
  provideRouter,
} from "@angular/router";
import { vi } from "vitest";

import { environment } from "../../../environments/environment";
import { SessionGateComponent } from "./session-gate.component";

describe("SessionGateComponent", () => {
  let fixture: ComponentFixture<SessionGateComponent>;
  let http: HttpTestingController;
  let router: Router;

  beforeEach(async () => {
    sessionStorage.clear();
    await TestBed.configureTestingModule({
      imports: [SessionGateComponent],
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
    fixture = TestBed.createComponent(SessionGateComponent);
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  afterEach(() => {
    http.verify();
    sessionStorage.clear();
  });

  function setToken(value: string): void {
    const input = fixture.nativeElement.querySelector(
      "#session-token",
    ) as HTMLInputElement;
    input.value = value;
    input.dispatchEvent(new Event("input"));
  }

  function submit(): void {
    const form = fixture.nativeElement.querySelector("form") as HTMLFormElement;
    form.dispatchEvent(new Event("submit"));
  }

  it("renders the connect form with a hint pointing to `data-sentinel serve`", () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain("Conectar ao Sentinel");
    expect(el.textContent).toContain("data-sentinel serve");
  });

  it("shows a required-field error when submitting an empty token", () => {
    submit();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain(
      "Informe um token para continuar.",
    );
    http.expectNone(`${environment.apiBaseUrl}/capabilities`);
  });

  it("shows an invalid-token error on a failed validation", () => {
    setToken("bad-token");
    fixture.detectChanges();
    submit();
    fixture.detectChanges();

    http
      .expectOne(`${environment.apiBaseUrl}/capabilities`)
      .flush({ detail: "unauthorized" }, { status: 401, statusText: "Unauthorized" });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      "Token inválido ou expirado",
    );
  });

  it("navigates to the dashboard on a successful connect", () => {
    const navigateSpy = vi
      .spyOn(router, "navigateByUrl")
      .mockResolvedValue(true);

    setToken("good-token");
    fixture.detectChanges();
    submit();
    fixture.detectChanges();

    http.expectOne(`${environment.apiBaseUrl}/capabilities`).flush([]);

    expect(navigateSpy).toHaveBeenCalledWith("/");
  });

  it("never puts the token in a URL or query string", () => {
    setToken("good-token");
    fixture.detectChanges();
    submit();

    const req = http.expectOne(`${environment.apiBaseUrl}/capabilities`);
    expect(req.request.urlWithParams).not.toContain("good-token");
    req.flush([]);
  });
});
