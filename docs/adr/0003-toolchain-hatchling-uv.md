# ADR 0003 — Build backend e toolchain (hatchling + uv)

**Status:** accepted
**Data:** Cycle 01 (ds-0001)

## Contexto

O projeto precisa de builds reproduzíveis, resolução de dependências rápida e
uma cadeia de ferramentas enxuta.

## Decisão

- Build backend: **hatchling** (PEP 517), pacote em src-layout.
- Gestor de ambiente/pacotes: **uv** (`uv run`, `uv add`).
- Qualidade: **ruff** (lint+format) e **mypy --strict**; testes com
  **pytest + pytest-cov**.
- `.python-version` fixa 3.12 para desenvolvimento; `requires-python >= 3.11`.

## Consequências

- `uv` resolve lockfile em segundos e instala em ambientes CI sem setup extra.
- src-layout garante que testes exercitam o pacote instalado, não o diretório.
- Dev pin em 3.12 evita que o uv escolha um interpretador mais novo (ex.: 3.14)
  que fujir do alvo de compatibilidade — decisão registrada após o problema
  real ocorrido no ds-0001.
