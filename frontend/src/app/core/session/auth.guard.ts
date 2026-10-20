import { inject } from "@angular/core";
import { CanActivateFn, Router } from "@angular/router";

import { SessionService } from "./session.service";

/**
 * Blocks feature routes until a session is established (ADR-0014).
 * Redirects to the session gate, preserving the originally requested
 * URL so the gate can return the user there after a successful
 * `establish()`.
 */
export const authGuard: CanActivateFn = (_route, state) => {
  const session = inject(SessionService);
  const router = inject(Router);

  if (session.isAuthenticated()) return true;

  return router.createUrlTree(["/session"], {
    queryParams: { redirect: state.url },
  });
};

/**
 * Keeps an already-authenticated user off the session gate — used on
 * the `/session` route itself.
 */
export const sessionGateGuard: CanActivateFn = () => {
  const session = inject(SessionService);
  const router = inject(Router);

  if (!session.isAuthenticated()) return true;

  return router.createUrlTree(["/"]);
};
