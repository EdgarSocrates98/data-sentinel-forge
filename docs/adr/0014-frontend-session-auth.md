# ADR-0014 — Frontend Session Authentication

Status: Accepted (Cycle 08.1, ds-0101)

## Context

The backend (`src/data_sentinel/api/app.py`, `bearer_auth` middleware)
requires `Authorization: Bearer <token>` on every `/api/v1/*` route
except `/api/v1/health` and the OpenAPI docs. Tokens expire after 4
hours. The Angular Control Center (`frontend/`) had no authentication
layer at all: every `ApiService` call and the investigation SSE stream
(`GET /investigations/{id}/stream`, consumed via `EventSource`) hit the
API without a token, so a real deployment behind the bearer-auth
middleware would see every request fail with 401 — including the live
stream, since `EventSource` cannot set custom headers.

## Decision

1. **Bearer token in `sessionStorage`**, never in the URL, query string,
   or `localStorage`. `SessionService` is the only writer; it persists a
   token only after validating it against a real authenticated endpoint
   (`GET /capabilities`), so a bad token is never stored.
2. **A functional `HttpInterceptorFn` (`authInterceptor`)** attaches the
   header to every `/api/v1/*` request (except `/health`) and, on a 401
   response, clears the session and routes to a session onboarding gate
   (`/session`) — not a dead end.
3. **`CanActivateFn` guards** (`authGuard`, `sessionGateGuard`) protect
   every feature route and keep an already-authenticated user off the
   gate.
4. **Fetch-based SSE, not `EventSource`**, for
   `investigation-stream.service.ts`. `EventSource` has no API for
   custom request headers, so it cannot carry the bearer token the
   backend requires. The stream is now read via `fetch()` +
   `ReadableStream` + `AbortController`, parsing `event:`/`data:`/`id:`
   frames by hand and supporting `Last-Event-ID` on reconnect. The
   public API of `InvestigationStreamService.open(url)` is unchanged.

### Alternatives considered

- **HttpOnly session cookie + BFF (backend-for-frontend) proxy.**
  Rejected for this cycle: it requires a new server component in front
  of the FastAPI app (or changing the FastAPI auth model to
  cookie-based CSRF-protected sessions), which is out of scope for a
  local-first, single-process tool (`data-sentinel serve`) and would
  duplicate the Origin/CSRF checks the backend middleware already does
  for mutations. Revisit if/when a multi-user hosted deployment exists.
- **Token in `localStorage`.** Rejected: survives browser restarts and
  is readable by any script in the origin for the lifetime of the
  profile, which is a larger blast radius than the 4h server-side TTL
  justifies. `sessionStorage` dies with the tab and matches the
  session's actual lifetime story better.
- **Token in the URL (query string).** Rejected outright: leaks into
  browser history, server access logs, and `Referer` headers.
- **Keep `EventSource`, authenticate via a short-lived query-string
  token minted just for the stream.** Rejected: reintroduces
  URL-embedded credentials and a second token-issuance surface for no
  benefit now that `fetch` can read a stream body directly.

## Consequences

- Every API call (`ApiService`) and the investigation stream now
  require a valid session; a clean browser is routed to `/session`
  before it can reach any feature route.
- `SessionService` tracks client-side expiry (`established-at` + the
  4h TTL) since the backend's 401 response does not currently carry an
  expiry timestamp — see the backend-contract gap noted below.
- The fetch-based SSE client does not get the browser's built-in
  auto-reconnect that `EventSource` provided; reconnect logic belongs
  to the consumer (`InvestigationDetailComponent` already treats a
  stream error as a terminal state with a manual retry, which this ADR
  does not change).

## Backend contract gap (reported, not worked around)

- `POST`-free routes still return a bare `{"detail": "unauthorized"}`
  on 401 with no expiry/issued-at metadata. The 4h TTL is tracked only
  client-side, from the moment `establish()` succeeds — if the server
  clock and client clock drift, or the server token was already
  partially aged (e.g. reused across tabs), the client's expiry
  estimate will be honest about *its own* uncertainty but cannot be
  exact without the backend returning real issuance/expiry data.

  Correction (cycle-08.1 review): the stream endpoint **does** emit
  `id: <seq>` frames and honors `Last-Event-ID` — the earlier claim
  that this support was inert was wrong. Reconnect remains a manual
  retry by design.
