# Cycle 08 — Final Report

**Decision: APPROVED WITH RESTRICTIONS**

## Scope

Production hardening, release engineering, and open-source homologation
over the Cycle 07 baseline (`8a6a07b`). 10 specs, ds-0090→ds-0099.

## Verified numbers (measured this cycle)

- **893 pytest passed**, 4 env-gated skips (real AWS creds).
- **64/64 ng tests** under Vitest (migrated from Karma, jsdom env).
- ruff clean; mypy strict clean (153 source files).
- Wheel `data_sentinel-0.1.0-py3-none-any` installs in a clean venv and
  runs `capabilities` + `investigate run` with real findings.
- Evaluation: precision 0.9286, recall 0.9286, 5 correct UNKNOWNs,
  0 forbidden violations, p50 0.081ms / p95 47.85ms.
- npm audit: 12 high → 8 high + 3 moderate (karma tree removed;
  2 critical tinypool eliminated via override; residual braces chain
  requires Angular 21 — documented).

## Delivered

| Spec | Delivery |
|---|---|
| ds-0090 | Baseline audit at `8a6a07b` — `docs/cycles/cycle-08-baseline.md` |
| ds-0091 | `OpsStore` versioned SQLite (PRAGMA user_version) for all operational entities; API restart recovery; auth hardening (rotate/revoke/lockout); §2.3 integrity checker |
| ds-0092 | AWS homologation — **BLOCKED_EXTERNAL** (no creds; no mocks used) |
| ds-0093 | Clean wheel install verified + `docs/installation.md` |
| ds-0094 | Real eval harness + measured metrics; surfaced 5 genuine product findings |
| ds-0095 | Karma→Vitest, audit reduction, CycloneDX SBOM + python-deps inventory |
| ds-0096 | Capability discovery + MCP verified; `docs/forge-integration.md` |
| ds-0097 | SemVer policy, OIDC release workflow (gated, unpublished), ADR-0012 |
| ds-0098 | A–Z homologation matrix — `docs/cycles/cycle-08-homologation.md` |
| ds-0099 | This report + consolidated docs |

## Real findings surfaced by the eval (backlog, not hidden)

1. `volume-growth` FN — fixture↔runner schema gap (`baseline_bytes` vs `baseline`).
2. `iceberg-small-files` — CONFIRMED finding with empty evidence_ids (contract violation).
3. `alert-recovery` FP — extra `missing_data` alert.
4. `dq_pass_rate`/`freshness_s` not in quality SIGNALS — silent metrics.
5. Spark analyzers on non-parseable input: all-UNKNOWN, 0% evidence (honest but thin).

## Restrictions (P1, documented)

- AWS real homologation: BLOCKED_EXTERNAL (`cycle-08-aws-homologation.md`).
- Remote CI: billing-blocked; local runbook in `release-readiness.md`.
- WebKit Playwright: `libavif16` missing on host.
- npm residual: 8 high braces-chain (Angular 20 webpack toolchain),
  3 moderate vitest-mocker — dev-only, documented in SECURITY-UPGRADE.md.
- Cross-platform: wheel is pure-Python; Windows/macOS runs defined in
  CI matrix but not executed remotely.
- Version remains 0.1.0; no publish (Grill Gate decision).

## P0 gates: all clear

No cloud mutation without consent, no secrets exposure, API hardened
(auth+TTL+Origin+CSRF+lockout+audit), no evidence fabrication, MCP
permission checks verified, no unauthorized publish path armed.
