# Changelog

All notable changes to Data Sentinel are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
