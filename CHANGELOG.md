# Changelog

All notable changes to Data Sentinel are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.5.0] - 2026-11-04

### Added
- **Guided install lifecycle + wizard** — install planning, receipts and
  host-aware guided flow on a real TTY; flags stay non-interactive.

## [0.4.0] - 2026-10-26

### Added

- `POST /api/v1/analyze/{id}` now accepts the full tool `inputSchema` —
  multi-input tools (`quality.detect_drift`, `lineage.impact`,
  `doctor.correlate`) and file-free tools (`emr.estimate_cost`) are
  callable through the API. File-like keys resolve under allowed roots
  with the extension allowlist; v1 `{"file": "..."}` stays valid.
- `sentinel.spark.analyze_plan` emits the parsed plan tree as a typed
  output (`plan` key; `ExecutionPlan.to_dict()` wire shape). The Angular
  plan explorer renders the operator tree.
- Operational schema v2: `ingestion_checkpoints` table with
  save/get/delete — resumable cursors for streaming ingestion.
- `X-Request-Id` on every API response (inbound header honored);
  `SentinelError` taxonomy mapped to `{detail, code, details,
  request_id}` envelopes; redacted 500 catch-all.
- Contract test `test_ts_contract_parity.py` validates
  `frontend/.../api.models.ts` field names against the Python wire
  shapes (8 interfaces).

### Changed

- **Distribution renamed to `data-sentinel-forge`** (PyPI name-policy;
  module stays `data_sentinel`, CLI stays `data-sentinel`). Install:
  `pip install data-sentinel-forge`.
- `PRAGMA busy_timeout=5000` on all SQLite stores (WAL concurrency).
- `ApiService.analyze` accepts a full inputs object; `AnalyzeRequest`
  generalized to the tool inputSchema shape.
- Phase-0 baseline audit: `docs/audits/pre-cycle-09-baseline.md`;
  cycle report: `docs/cycles/cycle-09-report.md`.

## [0.3.0] - 2026-10-23

### Fixed

- Changelog: PyPI publish for 0.2.2 recorded as blocked (approval-gated
  `pypi` environment).

## [0.2.2] - 2026-10-23

### Security

- Vendored `_installkit` backported 1.0.0 -> 1.0.4: stale-lock ownership tokens
  and reclaim race fix, credential redaction covering URL userinfo, unsafe-path
  refusals (`FORGE-INSTALL-UNSAFE-PATH`) in plan/apply/repair/uninstall/prune,
  atomic-write mode preservation, and unsafe ledger entries surfaced in
  `status()`/`doctor` as non-repairable.

## [0.2.1] - 2026-10-21

### Fixed

- CLI stdout/stderr reconfigured to UTF-8 at startup — report glyphs (e.g. `⋈`)
  no longer crash on Windows consoles defaulting to cp1252
  (`UnicodeEncodeError` in release smoke).
- Release workflow: `test_version` reads `__version__` dynamically;
  `install manifest` regenerated for 0.2.x; wheel test builds its own wheel
  when `dist/` is absent (verify-before-build ordering).

## [0.2.0] - 2026-10-21

### Added

- Integrations cycle (lf-0030): deterministic doctor x sentinel cross-correlation — `data-sentinel import doctor-bundle --correlate` and `import correlate` merge doctor findings into sentinel diagnostics anchored on declared evidence only (no confidence promotion, no causality claims); `sentinel.doctor.correlate` registry tool.

## [0.1.0] — 2026-10-21

First tagged release. Data Sentinel is an independent, offline-first,
deterministic diagnostics platform for data-engineering workloads —
Spark, AWS Glue, SQL, lakehouse and EMR — where every finding cites its
evidence and declares an honest confidence level.

### Added

- **Diagnostic core**: `analyze`, `sql analyze`, `spark
  explain|optimize`, `glue inspect|runs|diagnose`, `lakehouse
  metadata|access|policy|operation|compat`, `emr analyze|compare|cost`,
  `quality validate|import`, `lineage ingest|impact`, `investigate run`,
  `capabilities`, `agents`, `tools`, `report show|export`.
- **Evidence contract**: findings carry `evidence_ids` and statuses
  `CONFIRMED | PROBABLE | POSSIBLE | UNKNOWN`; missing evidence surfaces
  in `limitations` rather than false "healthy" conclusions.
- **Portable installer** (`data-sentinel install`): interactive and
  `--yes` flows; scopes project/workspace/user; profiles
  minimal/recommended/full; host adapters for Claude, Devin, Codex and
  Copilot (Cursor: partial, no catalog adapter); ownership-aware writes,
  ledger, rollback, drift detection, `status|doctor|repair|uninstall`,
  `install env` environment report.
- **Agentic surfaces**: 5 host skills (`data-sentinel-investigate`,
  `-spark-plan`, `-sql-review`, `-quality-drift`, `-report`) and 3 agent
  profiles (`sentinel-investigator`, `-reviewer`, `-spark-specialist`)
  shipped in the wheel; `forge.json`/`forge.agentic.json` manifests for
  Forge ecosystem discovery.
- **MCP server** (`mcp serve`): 20 tools over stdio, read-only roots,
  real handshake validation by the installer.
- **Optional AWS path**: `glue *` verbs behind the `aws` extra and
  credentials; read-only, with `--dry-run` collection preview.
- **Angular Control Center** (`frontend/`): investigations, reports,
  evidence explorer and observability UI.
- **API surface** behind the `api` extra.

### Security

- Asset integrity fail-closed via `MANIFEST.sha256` (LF-pinned for
  cross-platform checkout).
- No remote script execution, no writes outside the authorized scope,
  no silent overwrite of user-owned files, secrets redacted before
  persistence, environment reports emit set/unset only.
- CI matrix: Linux, macOS, Windows × Python 3.11/3.12.

### Known restrictions

- PyPI publication not yet performed; install from source or
  `pip install git+https://github.com/EdgarSocrates98/data-sentinel-forge`.
- Cursor host is partially supported (no full catalog adapter).
- Codex does not read project-scope `.mcp.json`; MCP needs user scope
  or `codex mcp add`.
- The Forge / forge-cli integration is manifest- and docs-level only.

[0.1.0]: https://github.com/EdgarSocrates98/data-sentinel-forge/releases/tag/v0.1.0

> **PyPI**: `v0.2.2` não publicado — workflow `Release` gated no
> environment `pypi` (trusted publisher + aprovação humana). Jobs de
> verify/smoke verdes; publish falhou por design até aprovação do dono.
