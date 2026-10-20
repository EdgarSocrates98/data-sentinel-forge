# Versioning Policy — Cycle 08 (ds-0097)

## Scheme

Semantic Versioning 2.0.0 — `MAJOR.MINOR.PATCH`.

Current: `0.1.0` (via `[tool.hatch.version]` → `src/data_sentinel/__init__.py`).

- **MAJOR**: breaking changes to CLI flags, `forge-contracts`, API
  paths, SQLite schema without migration path.
- **MINOR**: new analyzers/capabilities/tools, backwards-compatible
  schema migrations.
- **PATCH**: fixes, docs, internal refactors.

Pre-1.0: MINOR may break; PATCH must not. No 1.0 commitment without
owner sign-off.

## Changelog

`CHANGELOG.md` — Keep-a-Changelog format, one section per release.
Entries grouped by Added/Changed/Fixed/Removed/Security.

## Migration notes

Persisted-state changes (SQLite `user_version`) require a migration
step in `persistence/`; never silent drops. Document each bump in the
changelog entry.

## Compatibility policy

- Python ≥ 3.11 (single supported floor, tested on 3.12).
- `forge-contracts/1` is stable; a new contract version gets a new
  adapter path — old versions keep importing.
- API `/api/v1` is stable; breaking changes go to `/api/v2`.

## Release notes

Generated per tag: changelog section + verification evidence
(pytest count, wheel smoke, known restrictions).
