# Cycle 08.1 — Final Report (ds-0100 … ds-0108)

**Scope**: close Cycle-08 P0 gaps — frontend auth, real cross-browser E2E,
the 5 genuine eval findings, CI/release integrity, backend/MCP hardening.

**Commits**: `af87eff..859431f` on `main`
(`e9a255b`, `3bf5b3c`, `5981077`, `ae9ac2d`, `915d6dd`, `677929b`,
`1610fc8`, `859431f`)

## Measured results

| Metric | Cycle 08 | Cycle 08.1 |
|---|---|---|
| pytest | 893 passed | **921 passed**, 4 AWS-gated skips |
| Angular tests | 64 | **96** (Vitest) |
| Playwright e2e | broken-by-auth | **145 passed / 2 skipped / 0 failed — Chromium, Firefox, WebKit** |
| Eval precision / recall | 0.929 / 0.929 | **1.0 / 1.0** (31 scenarios) |
| Unsupported claims | 1 | **0** |
| Forbidden-phrase violations | 0 | 0 |
| Eval p50 / p95 | 0.081 / 47.85 ms | 0.121 / 4.09 ms |
| CI matrix | 6/6 green | **7/7 green** (+ minimal-install) + new frontend workflow |
| npm audit (prod deps) | — | **0 vulnerabilities** |

## Independent review (required gate)

A spec-reviewer subagent audited `af87eff..HEAD` findings-first and
returned **request-changes** with: 1 BLOCKER, 4 HIGH, 3 MEDIUM, ~14
LOW/NIT — every finding cited file:line and was verified before fixing.

| Severity | Finding | Resolution |
|---|---|---|
| BLOCKER | CORS registered first → `CORSMiddleware` innermost → every preflight OPTIONS on a protected route died at `bearer_auth` with a bare 401 (no `Access-Control-*`) → entire authenticated browser journey dead-on-arrival | CORS registered **last** (outermost); `test_cors_preflight_on_protected_path` added |
| HIGH | `authInterceptor` outermost ⇒ `httpErrorInterceptor` normalizes the 401 to `ApiError` first ⇒ `instanceof HttpErrorResponse` never matched ⇒ `expire()`+`/session` redirect dead code | match `err.status === 401` on any error shape |
| HIGH | SSE terminal event lost: `transition()` before `emit()` ⇒ terminal-state check could return before the event existed | emit-before-transition (terminal state ⇒ event committed) + store drain before return on terminal state |
| HIGH | `alert-{ms}` ids collide within one ms → `INSERT OR REPLACE` silently overwrote alerts | per-engine seq suffix `alert-{ms}-{n}` |
| HIGH | ds-0102 acceptance unmet at review time | completed by spec-implementer (below) |
| MEDIUM | recovery stamped the failure dedup slot → fail→recover→fail inside cooldown suppressed the new incident | recovery releases the slot |
| MEDIUM | `DECREASE_IS_BAD` honored only by the relative-threshold branch | direction applied to abs/z-score/trend branches |
| MEDIUM | no logout affordance | logout button in shell (auth'd only) → `session.clear()` + `/session` |
| LOW×~14 | fchmod+O_NOFOLLOW on token persist; `Content-Length` malformed → 400; `freshness_s`/`dq_pass_rate` kind map; `auth_failures` bounded; bearer scheme case-insensitive (RFC 7235); double `_redact`; events signal leaked across investigations; redirect param unconstrained; stale `id:`-frame claims in code+ADR | all fixed in `915d6dd` (+Windows `os.fchmod`/`PTH101` follow-ups `677929b`, `1610fc8`) |

## Per-spec evidence

- **ds-0100** — CI audit + `minimal-install` job: wheel installs and
  imports with zero extras + CLI runs. Green in CI and a clean local venv.
- **ds-0101** — Angular session auth (ADR-0014): bearer in
  `sessionStorage`, `authInterceptor`, `authGuard`/`sessionGateGuard`,
  `/session` gate (pt-BR-first), fetch-SSE with `Last-Event-ID`.
  Review gap (401 path dead at the interceptor seam) fixed; logout added.
- **ds-0102** — `e2e/authenticated.spec.ts` real-gate journey (invalid →
  real token → capabilities/agents → fixture investigation → SSE wire
  contract → findings → evidence → graph → reports → reload persistence →
  fresh-tab isolation → **second uvicorn over same SQLite for restart
  persistence** → quality/lineage → disabled watch + manual eval →
  remediation DRAFT→approve→dry-run→local-exec SKIPPED → request-ledger
  no-cloud/no-mutation audit). `.github/workflows/frontend.yml`: strict
  tsc ×3, ng test, build, 600 kB bundle gate, enforced prod-only npm
  audit, per-project e2e matrix, honest non-blocking webkit job.
  **Found & fixed 2 real bugs**: axe `scrollable-region-focusable` on
  /agents; 120 req/min bucket tripped by parallel workers (deterministic
  orchestration fix, backend untouched). **WebKit is green** — the
  anticipated `BLOCKED_EXTERNAL` did not materialize.
- **ds-0103** — backend audit `docs/cycles/cycle-08-1-backend-audit.md`:
  9 findings fixed; review added the CORS/SSE/bearer/content-length items.
- **ds-0104** — all 5 Cycle-08 eval findings fixed; eval rerun
  precision/recall 1.0. Follow-up: `drift_findings` dangling evidence ids
  → real `Evidence` objects.
- **ds-0105** — 5 real-uvicorn SSE tests (replay order/uniqueness,
  multi-client identical streams, `Last-Event-ID` resume, 404, mid-stream
  reconnect). Review added the terminal-event race fix.
- **ds-0106** — `execute_tool(allowed_roots=)` dead param wired; MCP
  enforces launch-cwd roots (`DATA_SENTINEL_MCP_ROOTS` extends);
  schema/denial/shutdown + evidence-integrity + LLM-ban tests.
- **ds-0107** — `release.yml` hardened (verified above); **no automatic
  publish**; `npm audit` step is report-only and now uploads the report
  as an artifact (honesty, not gating).
- **ds-0108** — this report + archive gate.

## §12 — The 15 mandatory criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | CI Python green on full matrix | ✅ | 7/7 jobs (ubuntu/macos/windows × py3.11/3.12 + minimal-install) — runs `39513587794`, `39517180230`, `39518096125` |
| 2 | CI Angular green | ✅ | `.github/workflows/frontend.yml` — run `39519801132`: quality (tsc×3, 96 ng, build, 600 kB gate, audit) + 5 playwright jobs all green |
| 3 | Authenticated frontend/backend E2E | ✅ | `e2e/authenticated.spec.ts` — ~145 pass on Chromium+Firefox+WebKit locally AND in CI (run `39519801132`) vs real spawned uvicorn |
| 4 | No confirmed finding without evidence | ✅ | `tests/unit/test_confirmed_evidence_contract.py` (AST + runtime) — 0 violations; Iceberg 2 sites fixed |
| 5 | Five eval findings treated | ✅ | ds-0104: eval rerun precision/recall **1.0/1.0**, 0 unsupported, 31 scenarios |
| 6 | No regression on previous cycles | ✅ | 921 pytest (up from 893) — all prior suites green; 96 ng tests |
| 7 | Authenticated API | ✅ | bearer_auth middleware + lockout + rotate/revoke — `test_auth_hardening.py`, `test_api_security.py` |
| 8 | Authenticated SSE | ✅ | fetch-SSE with bearer header; stream 401s unauthenticated; 5 real-uvicorn SSE tests |
| 9 | Persistence verified | ✅ | `InvestigationStore`/`OpsStore` restart/recovery/replay/concurrency/backup tests + e2e second-server restart check |
| 10 | Security audit executed | ✅ | `cycle-08-1-backend-audit.md` (9 findings) + independent review (1 BLOCKER + 4 HIGH + 3 MEDIUM, all fixed) |
| 11 | Valid Python + Angular builds | ✅ | `uv build` + twine check in release.yml; `ng build` clean (62 kB raw initial vs 600 kB gate) |
| 12 | MCP tested | ✅ | real stdio launch tests — init, tools/list, schema `input_schema`, permission denial as data, shutdown |
| 13 | Wheel in clean environment | ✅ | minimal-install CI job + local clean venv — core imports + CLI work with zero extras |
| 14 | Documentation updated | ✅ | ADR-0014 corrected, audit doc, residuals doc, this report, spec checkboxes |
| 15 | Reproducible release candidate | ✅ | hardened release.yml: verify → build → checksums → SBOMs → cross-OS smoke → OIDC-gated publish (unexecuted) |

## §13 — Corrected-error log (this cycle's fix trail)

- CI run `39515801508` failed: `os.fchmod` attr-defined on Windows mypy → `hasattr` fallback `os.chmod` → `Path.chmod` (`677929b`, `1610fc8`).
- Golden malformed-plan fixture outdated after parser classification fix → updated to "formato não reconhecido" + new unknown-operator fixture.
- `_RATE_BUCKETS` module-global → app-scoped state broke 26 tests → tests updated to `app.state.rate_buckets`.
- Playwright suite dead under authGuard → `seedSession` beforeEach + pinned test token (subagent).
- 8-worker parallelism tripped the 120 req/min loopback bucket → serialized `-auth` projects + stagger (documented, no backend change).
- axe `scrollable-region-focusable` violation on /agents → focusable region added.
- Frontend CI run `39518096227` failed twice before green: `uv run` inside Playwright lazily resolved an env without the `api` extra (180s webServer timeout) → `uv sync --all-extras` step; `ng serve` bound `::1` on CI runners while the url-check polled `127.0.0.1` → `--host 127.0.0.1` (`029ef71`, `44cd6c8`).
- `playwright install` took project names (`chromium-auth`) instead of browser names → `${BROWSER%-auth}` mapping.

## §13 — P0/P1/P2

- **P0**: none open (CORS preflight blocker found by review and fixed).
- **P1**: AWS live validation `BLOCKED_EXTERNAL`; `WatchRuntime`
  single-scheduler stall (backlog); dev-only npm advisories.
- **P2**: SSE replay 1000-event cap; `revoke()` requires restart (documented
  as design); MCP `invocation_id` static per tool.

## §13 — Packaging / MCP / Compatibility

- Wheel+sdist build reproducible; clean-venv install + CLI smoke verified
  on 3 OS × 2 Python in release.yml smoke matrix.
- MCP: official SDK, stdio, real init/list/deny — `tests/unit/test_mcp_stdio.py`.
- Compatibility: py3.11/3.12, ubuntu/macos/windows all green in CI.

## Vulnerabilities / residuals

- `npm audit --omit=dev`: **0 vulnerabilities**. Dev-chain advisories
  remain — classified per-advisory in `docs/security/frontend-residuals.md`.
- Accepted: `payload_limit` trusts `Content-Length` (local API);
  Windows ACL mapping of 0600 is best-effort; in-memory audit deque
  (durable trail is `OpsStore.audit`); SSE replay capped at 1000 events.
- Deferred (backlog): `WatchRuntime` single-scheduler loop — one watch's
  error backoff stalls the fleet; pre-existing, flagged by review.

## External limitations

- AWS real-world validation: `BLOCKED_EXTERNAL` (no credentials) — 4
  env-gated skips.
- Version stays `0.1.0`; release publication gated and unexecuted.

## Decision

**APPROVED WITH RESTRICTIONS** — no open P0; the independent review's
BLOCKER and all HIGHs are fixed and covered by new tests. P1: AWS live
validation; `WatchRuntime` scheduler stall (backlog).
