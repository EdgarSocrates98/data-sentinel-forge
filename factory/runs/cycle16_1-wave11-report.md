# Cycle 16.1 — Wave 11 report: data-sentinel-forge

Branch `cycle16_1/wave11` (off `main` @ `013a9a4`). Scope: install
lifecycle (`forge/InstallLifecycle/v1`), incremental reinstall,
workspace-manifest resource fix, PATH-independent MCP argv, compact L0
context, docs parity. Feature-freeze compliant — no new subsystem; the
lifecycle module is a byte-parity vendored copy of the canonical
`the-forge/src/theforge/install/lifecycle.py` (modulo `_SOURCE_SHA256`
stamp block, asserted by test).

## Files changed

- `src/data_sentinel/installation/lifecycle.py` (new) — vendored
  `forge/InstallLifecycle/v1` derivation: `derive_state`,
  `receipt_block`, `health_block`; states `planned`/`blocked`/`failed`/
  `applied`/`partially_applied`/`verified`/`unverified`/`ready`/
  `certified`. Derived from the document, never declared by the writer.
- `src/data_sentinel/installation/service.py` —
  `receipt["lifecycle"]` on `install`/`repair`/`uninstall` receipts;
  `doc["lifecycle"]` on `status`/`doctor`/`mcp-verify` health docs.
  Persisted install receipt is rewritten *after* `_register_context()`
  so a context `BLOCKED` no longer leaves a pre-context `completed`
  receipt on disk. `_resolved_mcp_command(spec)` feeds
  `InstallContext.mcp_command_resolved` (preserved absolute `cli.shim`
  → `sys.executable -m data_sentinel mcp serve` fallback).
  `_register()` merges into the existing global `cli` doc instead of
  replacing it — bootstrap `cli.shim` preserved. Docs-only installs
  (empty ledger + `.forge/context/` registry entry) report `healthy`
  with `context_registered: true`, never fake `unverified`.
- `src/data_sentinel/_installkit.py`, `src/data_sentinel/_forgecontext.py`
  — re-vendored canonical: per-file write accounting
  (`counts` per action + `written`/`written_bytes`; byte-identical
  assets not re-touched), `mcp_command_resolved` plumbed into
  `.mcp.json` argv, compact L0 forge block (identity/version/domains +
  pointers to capability manifest and `AGENT_PROTOCOL.md`).
- `forge.agentic.json`,
  `src/data_sentinel/installation/assets/manifest/resources.json` —
  `available` resources now declare checkout-relative `location`
  (`src/data_sentinel/installation/assets/agents/…`,
  `src/data_sentinel/knowledge/rules/…`) while keeping
  `packaged_location` package-relative; fixes the the-forge
  `test_workspace_manifest_resources_verify` failure.
- `src/data_sentinel/installation/assets/MANIFEST.sha256` — regenerated
  for the resources.json change.
- `pyproject.toml` — vendored `installation/lifecycle.py` added to
  ruff per-file ignores (canonical copy; stamped provenance before
  imports).
- `tests/unit/installation/test_lifecycle.py` (new) — state derivation
  table, receipt/health block shapes, canonical byte-parity after
  stripping the vendored stamp.
- `tests/unit/installation/test_cli.py` — resolved MCP argv, shim
  preservation, docs-only `context_registered` health.
- `tests/e2e/test_install_matrix.py` — incremental reinstall test:
  second identical install reports `written: 0`/`written_bytes: 0`,
  `unchanged` count covers all managed assets.
- Docs: `docs/installation.md`, `docs/cli.md`,
  `docs/installation/mcp.md`, `docs/installation/update-repair.md`,
  `docs/troubleshooting.md`, `CHANGELOG.md`, this report.

## Wave items → status

- Receipts/status compatible `forge/InstallLifecycle/v1`: **done** —
  every receipt and health doc carries the derived block; `completed`
  remains op-status only, never implies readiness.
- Incremental reinstall test: **done** — e2e test + real smoke
  (`8 unchanged / written 0 / written_bytes 0`).
- Workspace manifest resources: **done** — the-forge
  `test_workspace_manifest_resources_verify` passes; programmatic
  `install manifest --agentic` matches `forge.agentic.json`.
- Context metadata honest / minimal L0: **done** — compact block is
  identity + pointers; detail lives in the capability manifest and
  `AGENT_PROTOCOL.md`; docs-only health is truthful.
- Host surfaces sync: **done** — install-matrix tests cover
  claude/devin/codex/copilot rendering; cursor stays honestly partial
  (marker + `.mcp.json` only).
- MCP argv PATH-independent: **done** — live `.mcp.json` records
  `/abs/venv/bin/python -m data_sentinel mcp serve`; real handshake
  `mcp-handshake:PASS` + `mcp-invoke:PASS` in doctor.
- Docs vs actual parser: **done** — changed examples were executed
  (install/status/doctor smoke below); stale `.mcp.json` argv wording
  corrected.

## Gates run

- `pytest tests/unit/installation tests/e2e/test_install_matrix.py`
  → **145 passed**
- `pytest` (full suite) → **1100 passed, 4 skipped** (~197s)
- `ruff check .` → clean
- `mypy` (installation surface) → `Success: no issues found in 8 files`
- the-forge workspace gate:
  `test_workspace_manifest_resources_verify` → **PASS**;
  `manifest match: True`
- Live smoke (`data-sentinel` wheel CLI, tmpdir, `--host claude`):
  install → `completed` + `lifecycle.state=verified`,
  `counts={created:8, written:8, written_bytes:21534}`;
  `.mcp.json` argv = `[abs python, -m, data_sentinel, mcp, serve]`;
  AGENTS.md compact L0 block. Reinstall → `completed` +
  `lifecycle=verified`, `counts={unchanged:8, written:0,
  written_bytes:0}`. `install status` / `install doctor` → `healthy` +
  `lifecycle.state=ready`; doctor checks
  `ledger:PASS mcp-config:PASS mcp-handshake:PASS mcp-invoke:PASS
  forge-portal:NOT_APPLICABLE context-registry:PASS`.

## Review

Independent review required by the wave spec: implementer evidence is
recorded here; independent reviewer verdict is tracked by the
orchestrator (this report intentionally does not self-certify
acceptance).
