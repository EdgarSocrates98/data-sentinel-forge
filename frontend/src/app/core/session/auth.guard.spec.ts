import { provideHttpClient } from "@angular/common/http";
import { TestBed } from "@angular/core/testing";
import {
  RouterStateSnapshot,
  UrlTree,
  convertToParamMap,
  provideRouter,
} from "@angular/router";
import { vi } from "vitest";

import { authGuard, sessionGateGuard } from "./auth.guard";
import { SessionService } from "./session.service";

function runGuard(
  guard: typeof authGuard,
  url: string,
): boolean | UrlTree {
  return TestBed.runInInjectionContext(() =>
    guard(
      { paramMap: convertToParamMap({}) } as never,
      { url } as RouterStateSnapshot,
    ),
  ) as boolean | UrlTree;
}

describe("authGuard / sessionGateGuard", () => {
  let session: SessionService;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient()],
    });
    session = TestBed.inject(SessionService);
  });

  afterEach(() => sessionStorage.clear());

  it("authGuard blocks unauthenticated access and redirects to /session", () => {
    const result = runGuard(authGuard, "/investigations");
    expect(result).not.toBe(true);
    const tree = result as UrlTree;
    expect(tree.toString()).toContain("/session");
    expect(tree.queryParams["redirect"]).toBe("/investigations");
  });

  it("authGuard allows access once authenticated", () => {
    vi.spyOn(session, "isAuthenticated").mockReturnValue(true);
    const result = runGuard(authGuard, "/investigations");
    expect(result).toBe(true);
  });

  it("sessionGateGuard allows the gate when unauthenticated", () => {
    const result = TestBed.runInInjectionContext(() =>
      sessionGateGuard({} as never, {} as never),
    );
    expect(result).toBe(true);
  });

  it("sessionGateGuard redirects an authenticated user away from the gate", () => {
    vi.spyOn(session, "isAuthenticated").mockReturnValue(true);
    const result = TestBed.runInInjectionContext(() =>
      sessionGateGuard({} as never, {} as never),
    ) as UrlTree;
    expect(result.toString()).toBe("/");
  });
});
