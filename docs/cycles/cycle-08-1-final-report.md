# Cycle 08.1 — Final Report (ds-0100 … ds-0108)

**Scope**: close Cycle-08 P0 gaps — frontend auth, real cross-browser E2E,
the 5 genuine eval findings, CI/release integrity, backend/MCP hardening.

**Commits**: `af87eff..ae9ac2d` on `main`
(`e9a255b`, `3bf5b3c`, `5981077`, `ae9ac2d`)

## Measured results

| Metric | Cycle 08 | Cycle 08.1 |
|---|---|---|
| pytest | 893 passed | **909 passed**, 4 AWS-gated skips |
| Angular tests | 64 | **96** (Vitest) |
| Eval precision / recall | 0.929 / 0.929 | **1.0 / 1.0** (31 scenarios) |
| Unsupported claims | 1 | **0** |
| Forbidden-phrase violations | 0 | 0 |
| Eval p50 / p95 | 0.081 / 47.85 ms | 0.121 / 4.09 ms |
| CI matrix | 6/6 green | **7/7 green** (+ minimal-install job) |

## Per-spec evidence

- **ds-0100** — CI audit + `minimal-install` job: wheel installs and
  imports with zero extras (`core.contracts`, `capabilities`, spark
  parser) + CLI runs. Verified locally in a clean venv and in CI green.
- **ds-0101** — Angular session auth (ADR-0014): bearer in
  `sessionStorage`, `authInterceptor`, `authGuard`/`sessionGateGuard`,
  `/session` gate (pt-BR-first), `EventSource` replaced by authenticated
  fetch-SSE with `Last-Event-ID` support. 96/96 tests, `ng build` clean.
- **ds-0102** — Playwright authenticated journey + frontend CI workflow
  (see below).
- **ds-0103** — backend audit `docs/cycles/cycle-08-1-backend-audit.md`:
  **9 real findings fixed** — non-atomic token file (0604 window),
  stale-token revival on restart, audit log silently stopping at 10k,
  module-global rate buckets, shared-queue SSE split delivery,
  replay/subscribe gap, raw `str(exc)` into the event stream,
  `analyze` missing the extension allowlist, missing `WWW-Authenticate`.
- **ds-0104** — all 5 Cycle-08 eval findings fixed and the eval rerun:
  volume-growth FN (runner/contract-field gap + dead `link_changes`),
  Iceberg `CONFIRMED` without evidence (2 sites, evidence attached;
  AST+runtime contract test added), alert-recovery FP (`missing_data`
  gated), `dq_pass_rate`/`freshness_s` signals + `DECREASE_IS_BAD`
  direction, Spark non-plan input now emits a specific unsupported-format
  UNKNOWN. Follow-up: `drift_findings` emitted dangling synthetic
  evidence ids → now returns real `Evidence` objects.
- **ds-0105** — `tests/e2e/test_sse_reliability.py`: 5 tests over a real
  uvicorn server — ordered unique replay, identical multi-client streams,
  `Last-Event-ID` resume without dupes/gaps, 404, mid-stream
  disconnect+reconnect. Note: `id:` frames were verified to already exist
  (earlier claim of inert Last-Event-ID was wrong).
- **ds-0106** — `execute_tool(allowed_roots=)` was a **dead parameter**;
  wired through `_dispatch` to every file-reading branch. MCP server now
  enforces launch-cwd roots (`DATA_SENTINEL_MCP_ROOTS` extends) —
  `/etc/hostname` returns `PathViolationError` as data. New tests:
  MCP schema/denial/shutdown; evidence-integrity (every `evidence_ids`/
  `supporting_evidence` resolves); static LLM-import ban.
- **ds-0107** — `release.yml` rebuilt: backend verify (incl. security
  tests, clean-venv CLI smoke, real MCP stdio smoke, SHA256SUMS, CycloneDX
  SBOMs), frontend verify (npm ci, tsc×2, vitest, prod build, audit
  report), cross-platform smoke matrix (3 OS × 2 Python — wheel install,
  CLI analyze on real fixture, FastAPI boot + 401/bearer, SQLite
  restart), publish needs all + OIDC + `pypi` env + `RELEASE` input +
  in-job fails-closed guard + checksum verify. **No automatic publish.**
- **ds-0108** — this report + spec review/archive gate.

## Vulnerabilities / residuals

- Frontend npm audit: dev-chain advisories remain (braces chain,
  @vitest/mocker) — classified in `docs/security/frontend-residuals.md`;
  none reachable from the shipped bundle.
- Accepted: `payload_limit` trusts `Content-Length` (local API);
  Windows ACL mapping of 0600 is best-effort; in-memory audit buffer
  (durable trail is `OpsStore.audit`).

## External limitations (unchanged)

- AWS real-world validation: `BLOCKED_EXTERNAL` (no credentials).
- WebKit Playwright: see ds-0102 result below.
- Version stays `0.1.0`; release publication remains gated and unexecuted.

## Decision

**APPROVED WITH RESTRICTIONS** — no open P0. P1 items: AWS live
validation; residual npm advisories (Angular toolchain); SSE
`__end__`-only terminal signal for clients that connect mid-flight on an
already-terminal investigation is handled by the persisted-state check.
