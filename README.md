# Data Sentinel

**Intelligent Data Engineering & Agentic Diagnostics Platform** — ferramenta open source, independente e offline-first para investigar, analisar e diagnosticar workloads de engenharia de dados (Spark, AWS Glue, SQL, lakehouse) com evidência auditável.

> Status: **Cycle 01 — Foundation & Contracts** em andamento. Análises determinísticas, sem dependência obrigatória de nuvem ou de outros produtos.

## Instalação

```bash
uv sync --extra dev          # ambiente de desenvolvimento
uv run data-sentinel --help  # verificar instalação
```

Ou com pip: `pip install -e ".[dev]"`.

## Uso rápido

```bash
data-sentinel --help
data-sentinel version
```

## Desenvolvimento

```bash
uv run ruff check src tests   # lint
uv run mypy src               # tipagem estrita
uv run pytest -q              # testes
```

Documentação completa em `docs/` (em construção durante o Cycle 01).

## Licença

Apache-2.0 — veja `LICENSE`.
