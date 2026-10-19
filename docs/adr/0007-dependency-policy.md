# ADR 0007 — Dependency policy

**Status:** accepted
**Data:** Cycle 01 (ds-0001, revisado em ds-0009)

## Contexto

O Cycle 01 deve rodar offline e permanecer instalável por muito tempo; cada
dependência é dívida de supply-chain.

## Decisão

- Runtime mínimo: **pydantic**, **typer**, **sqlglot**. Somente isso.
- stdlib primeiro: `sqlite3`, `tomllib`, `json`, `hashlib`, `re`, `pathlib`.
- Futuras integrações (boto3, fastapi, uvicorn) entram como **extras
  opcionais** — nunca como dependência do núcleo.
- Nenhuma dependência nova é adicionada sem ADR ou justificativa no spec.
- Pins: versões mínimas (`>=`) em runtime; o lockfile do uv garante
  reprodutibilidade de dev/CI.

## Consequências

- `pip install data-sentinel` instala 3 dependências diretas — auditável.
- Offline garantido: nada no núcleo faz I/O de rede (verificado em doctor e
  na política de imports).
