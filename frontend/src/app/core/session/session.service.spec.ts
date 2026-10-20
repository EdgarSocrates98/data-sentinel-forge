import { provideHttpClient, withInterceptors } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { vi } from "vitest";

import { environment } from "../../../environments/environment";
import { authInterceptor } from "./auth.interceptor";
import { SESSION_TTL_MS, SessionService } from "./session.service";

describe("SessionService", () => {
  let service: SessionService;
  let http: HttpTestingController;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(SessionService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("starts unauthenticated with no stored token", () => {
    expect(service.isAuthenticated()).toBeFalse();
    expect(service.token()).toBeNull();
  });

  it("establish() validates the token against GET /capabilities and persists only on success", () => {
    let result: boolean | undefined;
    service.establish("good-token").subscribe((ok) => (result = ok));

    const req = http.expectOne(`${environment.apiBaseUrl}/capabilities`);
    expect(req.request.headers.get("Authorization")).toBe("Bearer good-token");
    req.flush([]);

    expect(result).toBeTrue();
    expect(service.isAuthenticated()).toBeTrue();
    expect(service.token()).toBe("good-token");
    expect(sessionStorage.getItem("ds-session-token")).toBe("good-token");
  });

  it("establish() does not persist a token rejected with 401", () => {
    let result: boolean | undefined;
    service.establish("bad-token").subscribe((ok) => (result = ok));

    http
      .expectOne(`${environment.apiBaseUrl}/capabilities`)
      .flush({ detail: "unauthorized" }, { status: 401, statusText: "Unauthorized" });

    expect(result).toBeFalse();
    expect(service.isAuthenticated()).toBeFalse();
    expect(service.token()).toBeNull();
    expect(sessionStorage.getItem("ds-session-token")).toBeNull();
  });

  it("establish() rejects an empty token without making a request", () => {
    let result: boolean | undefined;
    service.establish("   ").subscribe((ok) => (result = ok));
    expect(result).toBeFalse();
    http.expectNone(`${environment.apiBaseUrl}/capabilities`);
  });

  it("never stores the token in the URL or query string", () => {
    service.establish("good-token").subscribe();
    const req = http.expectOne(`${environment.apiBaseUrl}/capabilities`);
    expect(req.request.url).not.toContain("good-token");
    expect(req.request.urlWithParams).not.toContain("good-token");
    req.flush([]);
  });

  it("clear() removes the token from memory and sessionStorage", () => {
    service.establish("good-token").subscribe();
    http.expectOne(`${environment.apiBaseUrl}/capabilities`).flush([]);

    service.clear();
    expect(service.isAuthenticated()).toBeFalse();
    expect(sessionStorage.getItem("ds-session-token")).toBeNull();
  });

  it("expire() clears the session and flags it as expired", () => {
    service.establish("good-token").subscribe();
    http.expectOne(`${environment.apiBaseUrl}/capabilities`).flush([]);

    service.expire();
    expect(service.isAuthenticated()).toBeFalse();
    expect(service.isExpired()).toBeTrue();
  });

  it("treats a session past the client-side TTL as unauthenticated", () => {
    service.establish("good-token").subscribe();
    http.expectOne(`${environment.apiBaseUrl}/capabilities`).flush([]);

    const future = Date.now() + SESSION_TTL_MS + 1000;
    vi.spyOn(Date, "now").mockReturnValue(future);

    expect(service.isAuthenticated()).toBeFalse();
  });

  it("acknowledgeExpiry() dismisses the expired flag", () => {
    service.expire();
    expect(service.isExpired()).toBeTrue();
    service.acknowledgeExpiry();
    expect(service.isExpired()).toBeFalse();
  });
});
