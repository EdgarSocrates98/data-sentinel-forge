# Release Readiness — Cycle 08 (ds-0097)

Status: **READINESS ONLY** — Grill Gate decision: no PyPI publish, no
version bump this cycle.

## Checklist

| Item | Status | Evidence |
|---|---|---|
| SemVer policy | DONE | `docs/versioning.md` |
| Changelog | PARTIAL | `CHANGELOG.md` exists; needs per-release entry at RC |
| Migration notes | DONE | versioning.md + `persistence/` user_version migrations |
| Trusted Publishing (OIDC) | PREPARED | `.github/workflows/release.yml` — `pypi` env + `id-token: write`, manual dispatch + RELEASE confirm |
| CI (lint/type/test x-platform) | **GREEN** | `ci.yml` matrix 6/6 jobs green — real Windows/macOS bugs fixed in `349fa99`/`57ce72c` |
| Local reproducible runbook | DONE | below |
| Angular distribution | DECIDED | ADR-0012 |
| RC artifacts | DONE | `dist/` wheel+sdist build clean; `twine check` deferred to CI |

## CI billing — honest status

Remote CI is **live** — repo went public during Cycle 08. Last verified
run: 6/6 matrix jobs green (ubuntu/macos/windows × py3.11/3.12) on
`57ce72c`. The local reproducible run remains the offline fallback:

```bash
uv sync --extra dev
uv run ruff check src tests && uv run mypy src && uv run pytest -q
uv run python -m build && uvx twine check dist/*
```

Last local run: 892 passed, 4 env-gated skips, ruff+mypy clean,
wheel installs and runs in a clean venv.

## RC smoke tests (executed)

- Clean venv wheel install → `data-sentinel capabilities` (13),
  `investigate run` → real findings. See `docs/installation.md`.

## To publish (requires owner approval)

1. Create GitHub environment `pypi` with required reviewers.
2. Register Trusted Publisher on PyPI for this repo/workflow.
3. Bump version + changelog entry.
4. `workflow_dispatch` with `confirm=RELEASE`.
