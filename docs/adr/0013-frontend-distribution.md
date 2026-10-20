# ADR 0013 — Distribuição do frontend Control Center: build estático separado

**Status:** accepted
**Data:** Cycle 06 (ds-0079, §15 "Distribuição — decidir via ADR")

## Contexto

§15 pede avaliar duas estratégias para o bundle Angular de produção:

1. **Servir `frontend/dist/` pelo backend** (FastAPI montando static files).
2. **Distribuição separada** — bundle estático servido por qualquer servidor
   estático (ou `ng serve` em dev), consumindo a API via `apiBaseUrl`.

## Decisão

Distribuição **separada** (opção 2), neste ciclo.

- O pacote Python (`data-sentinel`) continua independente: a wheel não
  carrega ~350 kB de assets JS/CSS nem aplica binding estático no app
  factory — zero impacto em quem só usa CLI/API.
- Não há servidor obrigatório duplo "para sempre": o bundle é estático e
  qualquer static server (`serve -s`, nginx, `ng serve`) resolve; em dev,
  `ng serve` dá HMR. O CORS restrito da API (`localhost:4200` apenas) torna
  explícito que o par esperado é local.
- Servir o SPA pelo FastAPI exigiria acoplar `frontend/dist` ao wheel/sdist
  (hatchling) e introduziria um runtime concern na `api/app.py` — viola a
  fronteira "camada web não toca empacotamento do core".
- Trade-off aceito: usuário final que quiser o portal roda dois processos
  (API + static server). Documentado em `docs/guides/control-center.md`.

## Consequências

- `pyproject.toml`/wheel **inalterados**; `frontend/` permanece fora do
  pacote Python.
- Revisitar no Cycle 07+ **somente** se surgir consumidor que precise de
  single-process (ex.: modo `data-sentinel serve --with-ui` montando
  `dist/` quando presente — não implementado agora).
- O `--root`/`_safe_path` da API já delimita quais arquivos locais ela pode
  ler — servir SPA estático não passaria por esse guard (seria static mount
  separado), mais uma razão para manter separado neste ciclo.
