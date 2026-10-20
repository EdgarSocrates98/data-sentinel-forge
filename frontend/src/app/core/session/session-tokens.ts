import { HttpContextToken } from "@angular/common/http";

/**
 * Carries a one-off candidate token for a single request (used by
 * `SessionService.establish()` / `ApiService.validateToken()` to probe
 * `GET /capabilities` before any token is persisted). When set, it wins
 * over the stored session token for that request only.
 *
 * Kept in its own module (ADR-0014) so `ApiService` and
 * `authInterceptor` can both depend on it without a
 * `api.service -> auth.interceptor -> session.service -> api.service`
 * import cycle.
 */
export const SESSION_CANDIDATE_TOKEN = new HttpContextToken<string | null>(
  () => null,
);
