import { HttpInterceptorFn } from "@angular/common/http";
import { inject } from "@angular/core";
import { Router } from "@angular/router";
import { catchError, throwError } from "rxjs";

import { environment } from "../../../environments/environment";
import { SESSION_CANDIDATE_TOKEN } from "./session-tokens";
import { SessionService } from "./session.service";

/** Routes exempt from the bearer header (mirrors backend `open_paths`). */
const OPEN_PATH_SUFFIXES = ["/health"];

/**
 * Attaches `Authorization: Bearer <token>` to every request against the
 * Control Center API (ADR-0014). On a 401 from the API, clears the
 * session and routes to the session gate — never a dead end.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const session = inject(SessionService);
  const router = inject(Router);

  const isApiRequest = req.url.startsWith(environment.apiBaseUrl);
  const isOpenPath = OPEN_PATH_SUFFIXES.some((suffix) =>
    req.url.endsWith(suffix),
  );

  const candidate = req.context.get(SESSION_CANDIDATE_TOKEN);
  const token = candidate ?? session.token();

  let outgoing = req;
  if (isApiRequest && !isOpenPath && token) {
    outgoing = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }

  return next(outgoing).pipe(
    catchError((err: unknown) => {
      // Match on `status`, not `instanceof HttpErrorResponse`: this
      // interceptor is registered outermost, so by the time its
      // catchError runs, httpErrorInterceptor has already normalized
      // the error into an ApiError — the raw HttpErrorResponse never
      // arrives here (review).
      if (
        isApiRequest &&
        !isOpenPath &&
        !candidate &&
        (err as { status?: number })?.status === 401
      ) {
        session.expire();
        void router.navigate(["/session"], {
          queryParams: { reason: "expired" },
        });
      }
      return throwError(() => err);
    }),
  );
};
