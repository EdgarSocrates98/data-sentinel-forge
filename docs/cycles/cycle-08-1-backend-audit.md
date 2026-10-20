# Cycle 08.1 — Backend hardening audit (ds-0103, §6)

Scope: `src/data_sentinel/api/app.py` + supporting security paths.
Method: line-by-line read of the whole app factory + targeted tests for
each finding. Status: all real issues **fixed**, none merely annotated.

## Findings fixed

| # | Finding | Fix | Test |
|---|---------|-----|------|
| 1 | Token file written with default umask then chmod — a window existed where `session-token` was world-readable | `os.open(..., 0o600)` — mode applies atomically at `O_CREAT`; POSIX-verified | `test_token_file_0600_from_creation` |
| 2 | Stale token file revived: `_load()` accepted any file and reset the TTL clock, so a leaked token gained a fresh 4h window on every restart | file `st_mtime` older than TTL → regenerate | `test_stale_token_file_rejected` / `test_fresh_token_file_reused` |
| 3 | `_AUDIT_LOG` silently **stopped auditing** after 10 000 entries (append guarded by length check) | `deque(maxlen=10_000)` — rotates oldest, never stops | `test_audit_log_rotates_never_stops` |
| 4 | `_RATE_BUCKETS` module-global shared across app instances and unbounded per-client (same class of bug as the auth-lockout leak fixed earlier) | moved into `create_app` (app-scoped via `app.state.rate_buckets`) + `_MAX_RATE_CLIENTS` cap | `test_rate_limit_enforced` updated |
| 5 | **SSE isolation broken**: a single queue per investigation meant two concurrent stream clients split live events (each `q.get()` consumes for one client only) | per-subscriber fan-out — `subscribe()`/`unsubscribe()`; emit broadcasts to every attached queue; `__end__` broadcast to all | `test_sse_subscriber_fanout` |
| 6 | Replay gap: subscribing *after* persisted replay could lose live events emitted in between | subscribe **before** replay; live queue dedupes by `seq` (`item["seq"] <= last` skipped) | covered by existing stream/e2e tests |
| 7 | `INVESTIGATION_FAILED` emitted raw `str(exc)` — absolute paths/secrets could reach the SSE stream (redact masks dict keys, not string values) | `_safe_error()` strips `Path.home()`/`Path.cwd()` prefixes, truncates to 500 chars | `test_safe_error_strips_paths` |
| 8 | `POST /analyze/{id}` skipped `ALLOWED_FILE_EXTS` (inconsistent with `/investigations` file inputs) | same extension allowlist applied | extended `test_extension_allowlist` |
| 9 | 401 responses lacked `WWW-Authenticate: Bearer` | header added | `test_401_has_www_authenticate` |

## Audited and accepted as-is

- **Host/DNS-rebinding guard** (`local_guard`): rejects non-local hosts when auth is on.
- **Origin/CSRF guard**: mutations with a non-local `Origin` rejected; non-browser clients (no Origin) unaffected — correct scope.
- **CORS**: localhost:4200/127.0.0.1:4200 only, GET/POST only.
- **Rate limit**: 120 req/min per client; lockout after 10 auth failures/60s.
- **`_safe_path`**: `resolve()` before root check — symlinks escaping the root are rejected via the resolved target.
- **Auth check**: `secrets.compare_digest`, TTL rotation on access, explicit rotate/revoke endpoints.
- **No DELETE/PUT verbs**, no AWS-action endpoints, `source=aws` rejected on watches — verified by `test_no_glue_job_cancellation_endpoint`.
- **SSE `id:` frames already emitted** (`id: {seq}` on replay and live) — `Last-Event-ID` replay is real, not inert. (An earlier implementation note claimed frames were missing; verification of `stream()` proved otherwise.)

## Accepted limitations (documented, not bugs)

- `payload_limit` reads `Content-Length` — a chunked body without the
  header bypasses the cap. Local API behind bearer auth; uvicorn-level
  limits apply. Recorded as accepted risk.
- Windows: `os.open` mode bits map imperfectly to ACLs — the 0600 test is
  POSIX-only; Windows relies on the per-user profile dir.
- Audit log is in-memory; process restart loses it (persisted ops audit
  lives in `OpsStore.audit` — separate, durable trail).
