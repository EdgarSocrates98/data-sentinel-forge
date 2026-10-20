# Cycle 08 — Baseline Audit (08.0)

Auditado em 2026-10-20T15:20:08Z no HEAD real.

| Item | Estado medido |
|---|---|
| SHA | 8a6a07b |
| Python | 3.12 |
| pytest | **871 passed, 4 skipped** (env-gated AWS) |
| ruff check src tests | clean |
| mypy src | clean (151 files) |
| python -m build | data_sentinel wheel+sdist OK |
| Angular | 20.3 — 64/64 ng tests ChromeHeadless |
| ng build | clean |
| npm audit | 12 high — todas dev-only (braces/micromatch chain, sem fix upstream; mitigação = migração Vitest ds-0095) |
| Golden datasets | 30 cenários cycle7 |
| Capabilities | 15+ descriptors |
| MCP tools | 20 tools manifestadas |
| Especialistas | 18 (12 + 6 EMR) |
| Conectores AWS | boto3 allowlist 8 ações read-only |
| CI remota | bloqueada por billing do repo privado |
| Persistência | investigações SQLite; snapshots/watches/plans in-memory (corrigido em ds-0091) |

## Pendências conhecidas

- Estado operacional da API (snapshots/watches/plans) volátil por
  restart — ds-0091 corrige.
- Homologação AWS real: BLOCKED sem credenciais non-prod.
- Publish PyPI: readiness only (Grill Gate ds-009x #4).
- Versão do pacote: conforme pyproject.toml no HEAD.
