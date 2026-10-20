# Data Sentinel

**Intelligent Data Engineering & Agentic Diagnostics Platform.**

Ferramenta open source (Apache-2.0) para investigar, analisar e explicar
problemas em workloads de engenharia de dados — logs Spark/Glue, queries SQL,
jobs e ambientes lakehouse — com diagnósticos **apoiados em evidência
auditável**. Nada de causa-raiz inventada: todo achado cita a evidência que o
sustenta e declara seu nível de confiança.

## O que é

- **Análise determinística primeiro**: analyzers executam regras curadas sobre
  artefatos locais; resultados fracos ficam `PROBABLE`/`POSSIBLE`/`UNKNOWN` em
  vez de virar diagnóstico fabricado.
- **Offline por padrão**: analisa logs e SQL locais sem nenhuma chamada de
  rede ou credencial cloud.
- **Read-only**: nunca altera recursos de produção; guardas de caminho,
  tamanho e sanitização protegem a entrada.
- **Auditoria built-in**: evidências são sanitizadas (segredos redigidos) e
  persistidas em SQLite local junto ao relatório versionado.

## Instalação

Requer Python ≥ 3.11.

```bash
# via uv (recomendado para desenvolvimento)
uv sync
uv run data-sentinel --help

# via pip
pip install .
data-sentinel --help
```

Detalhes: [docs/installation.md](docs/installation.md).

## Quickstart

```bash
# Analisar um log de Glue/Spark (saída real abaixo)
data-sentinel analyze --file fixtures/logs/glue_oom.log

# Análise estática de SQL (AST SQLGlot, dialetos spark/trino)
data-sentinel sql analyze --file fixtures/joins/high_volume_4tables.sql --dialect spark

# Plano físico Spark (EXPLAIN) → árvore + estratégias + limitações
data-sentinel spark explain --file fixtures/plans/sort_merge_join.txt

# Pipeline composto: SQL + joins/cardinalidade + config advisor
data-sentinel spark optimize --sql query.sql --stats stats.json --config spark-defaults.conf

# AWS Glue read-only (requer [aws] + credenciais)
data-sentinel glue runs --job meu-job --limit 10 --region us-east-1
data-sentinel glue diagnose --job meu-job --run-id jr_abc --region us-east-1

# Saúde da instalação / capacidades / relatórios
data-sentinel doctor
data-sentinel capabilities
data-sentinel report show --id <report_id> --format markdown
```

Saída real de `analyze` sobre `fixtures/logs/glue_oom.log`:

```text
relatório 79e1efef4cd84f94882c76914aa9b760 (schema 1.0.0)
resumo: 1 achado(s): CONFIRMED=1

[HIGH/CONFIRMED] out_of_memory
  Assinatura inequívoca de java.lang.OutOfMemoryError indica que driver ou
  executor estourou o heap disponível. 2 ocorrência(s) no log analisado.
  evidência: fixtures/logs/glue_oom.log:5
    ... Lost task 0.1 ... : java.lang.OutOfMemoryError: Java heap space
  recomendação: Aumentar spark.driver.memory ou spark.executor.memory
  ...
```

Mais exemplos: [examples/README.md](examples/README.md) e
[docs/evidence/](docs/evidence/) (saídas capturadas de comandos reais).

## Códigos de saída

`0` sucesso · `1` erro de domínio/usuário · `2` erro de uso · `3` erro interno.
Ver [ADR 0006](docs/adr/0006-exit-code-scheme.md).

## Documentação

| Doc | Conteúdo |
|---|---|
| [docs/installation.md](docs/installation.md) | Instalação e requisitos |
| [docs/cli.md](docs/cli.md) | Referência dos comandos |
| [docs/configuration.md](docs/configuration.md) | Perfis, fontes, precedência |
| [docs/architecture.md](docs/architecture.md) | Arquitetura e módulos |
| [docs/security.md](docs/security.md) | Guardas, redação, postura read-only |
| [docs/development.md](docs/development.md) | Setup de dev, testes, lint |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Erros comuns |
| [docs/roadmap.md](docs/roadmap.md) | Cycles 02–08 e backlog do Cycle 02 |
| [docs/validation-matrix.md](docs/validation-matrix.md) | Matriz de validação com evidências |
| [docs/cycle-01-report.md](docs/cycle-01-report.md) | Relatório final do Cycle 01 |
| [docs/cycles/cycle-02-final-report.md](docs/cycles/cycle-02-final-report.md) | Relatório final do Cycle 02 |
| [docs/guides/](docs/guides/) | Guias por funcionalidade (Glue, CloudWatch, plano, SQL, joins, config) |
| [docs/examples/](docs/examples/) | Exemplos executáveis com saídas reais |
| [docs/adr/](docs/adr/) | Decisões arquiteturais |

## Estrutura

```text
src/data_sentinel/
├── core/          # contracts, configuration, security, exceptions
├── analyzers/     # registry + spark/{log,plans,joins,config} + sql + cloudwatch
├── connectors/    # aws/{glue,cloudwatch_logs} — extra [aws], read-only
├── diagnostics/   # orchestrator + correlation + timeline
├── reporting/     # renderers terminal/JSON/Markdown
├── persistence/   # SQLite store + migrations (stdlib)
├── api/           # contracts (readiness — sem servidor neste ciclo)
├── cli/           # Typer app
└── ...            # placeholders: mcp/, intelligence/, ...
```

## Estado do projeto

**Cycle 02 implementado** — conectores AWS read-only (Glue, CloudWatch)
com validação por mocks/Stubber, analyzer de plano físico Spark,
inteligência de joins/cardinalidade, SQL analyzer v0.2 (AST SQLGlot,
dialetos spark/trino), config advisor, orquestrador determinístico, CLI
com grupos novos e relatórios Markdown. **360 testes, cobertura 88%** —
evidência em [docs/cycles/cycle-02-validation.md](docs/cycles/cycle-02-validation.md)
e [docs/cycle-01-report.md](docs/cycle-01-report.md).

## Licença

Apache-2.0 — ver [LICENSE](LICENSE).

## Cycle 03 — Lakehouse (Iceberg, Lake Formation, cross-account)

```bash
data-sentinel lakehouse metadata -f metadata.json   # Iceberg metadata
data-sentinel lakehouse access   -f contexto.json   # cross-account
data-sentinel lakehouse policy   -f policy.json     # IAM/S3/KMS offline
data-sentinel lakehouse operation -f merge.sql      # MERGE/APPEND
data-sentinel lakehouse compat --runtime glue-5.1 --operation merge \
    --access-mode fgac                              # compatibilidade
```

Ver `docs/cycles/cycle-03-final-report.md` e guias em `docs/guides/`.
