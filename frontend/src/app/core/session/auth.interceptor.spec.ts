import {
  HttpClient,
  provideHttpClient,
  withInterceptors,
} from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { Router, provideRouter } from "@angular/router";
import { vi } from "vitest";

import { environment } from "../../../environments/environment";
import { authInterceptor } from "./auth.interceptor";
import { SessionService } from "./session.service";

describe("authInterceptor", () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let session: SessionService;
  let router: Router;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    session = TestBed.inject(SessionService);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    httpMock.verify();
    sessionStorage.clear();
  });

  it("attaches the stored bearer token to API requests", () => {
    session.establish("tok-1").subscribe();
    httpMock.expectOne(`${environment.apiBaseUrl}/capabilities`).flush([]);

    http.get(`${environment.apiBaseUrl}/agents`).subscribe();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/agents`);
    expect(req.request.headers.get("Authorization")).toBe("Bearer tok-1");
    req.flush([]);
  });

  it("does not attach a header when there is no session", () => {
    http.get(`${environment.apiBaseUrl}/agents`).subscribe({ error: () => undefined });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/agents`);
    expect(req.request.headers.has("Authorization")).toBeFalse();
    req.flush({}, { status: 401, statusText: "Unauthorized" });
  });

  it("does not attach a header to /health", () => {
    session.establish("tok-1").subscribe();
    httpMock.expectOne(`${environment.apiBaseUrl}/capabilities`).flush([]);

    http.get(`${environment.apiBaseUrl}/health`).subscribe();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/health`);
    expect(req.request.headers.has("Authorization")).toBeFalse();
    req.flush({});
  });

  it("clears the session and routes to the gate on a 401", async () => {
    session.establish("tok-1").subscribe();
    httpMock.expectOne(`${environment.apiBaseUrl}/capabilities`).flush([]);
    expect(session.isAuthenticated()).toBeTrue();

    const navigateSpy = vi.spyOn(router, "navigate").mockResolvedValue(true);

    http.get(`${environment.apiBaseUrl}/agents`).subscribe({ error: () => undefined });
    httpMock
      .expectOne(`${environment.apiBaseUrl}/agents`)
      .flush({ detail: "unauthorized" }, { status: 401, statusText: "Unauthorized" });

    expect(session.isAuthenticated()).toBeFalse();
    expect(session.isExpired()).toBeTrue();
    expect(navigateSpy).toHaveBeenCalledWith(
      ["/session"],
      expect.objectContaining({ queryParams: { reason: "expired" } }),
    );
  });

  it("does not treat the validation request itself as a session expiry on 401", () => {
    session.establish("bad-token").subscribe((ok) => expect(ok).toBeFalse());
    httpMock
      .expectOne(`${environment.apiBaseUrl}/capabilities`)
      .flush({ detail: "unauthorized" }, { status: 401, statusText: "Unauthorized" });

    expect(session.isExpired()).toBeFalse();
  });
});
