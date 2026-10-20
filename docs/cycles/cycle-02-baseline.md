# Cycle 02 — Baseline Audit

Auditoria do estado do Cycle 01 antes da implementação do Cycle 02, conforme
§1 do `prompt_evo_cycle2.md`. Toda afirmação abaixo deriva de comando
executado nesta sessão — ver `factory/runs/ds-0010.verification.log`.

## Estado encontrado

- Repositório: monólito modular `src/data_sentinel/` (49 arquivos fonte),
  `hatchling`+`uv`, Python 3.12 em dev (`.python-version`), `requires-python
  >=3.11`.
- Commits do Cycle 01: `f1fcfaf`..`b5f6b9f` — 9 specs (ds-0001..ds-0009)
  implementados, verificados e arquivados em `factory/specs/archive/2026/`.
- Não-verificação da homologação do Cycle 01: este documento **não
  redeclara** o ciclo homologado — ele re-executou a suite agora (abaixo) e
  distingue verificação nova de evidência herdada (`docs/evidence/`).

## Verificação executada agora (ambiente limpo)

| Comando | Resultado |
|---|---|
| `rm -rf .venv && uv sync` | instalação limpa OK |
| `uv run pytest -q` | **168 passed** |
| `uv run ruff check src tests` | All checks passed |
| `uv run mypy src` | 49 arquivos, 0 issues |
| `uv build` | `data_sentinel-0.1.0` wheel+sdist |
| `data-sentinel version` | `data-sentinel 0.1.0` |
| `analyze --file fixtures/logs/mixed.log --json` | relatório real (2 achados) |
| `data-sentinel doctor` | todos os checks PASS |

## Gap encontrado e corrigido nesta auditoria

`uv sync` puro **não instalava** as dev-deps (estavam em
`[project.optional-dependencies] dev`, que exige `--extra dev`; pip usa o
extra, uv não). Corrigido: adicionado `[dependency-groups] dev` — agora
`uv sync` instala tudo e `pip install ".[dev]"` continua funcionando.
Registrado no commit do ds-0010.

## Funcionalidades existentes (reusáveis)

- Contratos públicos versionados (`core/contracts`, `schema_version=1.0.0`,
  schemas exportados em `schemas/`).
- Config 5 camadas + perfis economy/balanced/deep/offline
  (`core/configuration`).
- Path guard, leitura limitada, sanitização ANSI/controle, redação de
  segredos (`core/security`) — usados por analyzers e store.
- Protocolo de analyzer + registry (`analyzers/protocol.py`,
  `analyzers/registry.py`).
- Analyzer de log Spark/Glue (9 padrões) e SQL estático SQLGlot (8 checks).
- Store SQLite stdlib + migrations (`persistence/`).
- CLI Typer: `analyze`, `report`, `doctor`, `capabilities`, `config show`,
  `version` — PT-BR, exit codes 0/1/2/3.
- Placeholders já existentes: `connectors/aws/`, `diagnostics/`,
  `analyzers/glue/`, `analyzers/cost/`, `api/`, `mcp/` (vazios desde ds-0001).

## Compatibility Gate (§1.3)

| Interface | Estado | Interface concreta |
|---|---|---|
| Plugins de análise | adequada | `Analyzer` ABC + `registry.register` (rejeita duplicados) |
| Conectores | adequada | pacote `connectors/aws/` placeholder + allowlist virá no conector (ds-0011) |
| Evidências | adequada | `Evidence` + `sanitize_evidence_excerpt` como ponto único |
| Findings | adequada | `Finding` com `status` CONFIRMED/…/UNKNOWN |
| Relatórios | adequada | `DiagnosticReport` versionado, JSON round-trip testado |
| Configurações | adequada | `SentinelConfig` + `allowed_roots` + `allow_network` por perfil |
| Persistência | adequada | `SentinelStore` — relatórios e evidências já persistem |
| CLI | adequada | Typer multi-comando, padrão de erro/exit estável |
| Exportação JSON | adequada | `to_json`/`model_dump` + schemas em `schemas/` |

Evoluções feitas neste spec (aditivas, sem quebra — schema segue `1.0.0`
conforme regra de minor em [ADR 0002](../adr/0002-contract-versioning.md)):

- `SourceType` ganhou `SPARK_PLAN`, `GLUE_JOB`, `CLOUDWATCH_LOG`
  (artefatos novos do ciclo). Schemas re-exportados.
- `AnalysisResult.duration_ms` — analyzers passam a poder informar duração
  (requisito §2.2).
- Pacote `reporting/` criado (renderers entram no ds-0017).

## Riscos

- boto3 só entra como extra `[aws]` — conectores devem degradar limpo sem ele.
- Fidelidade de mocks ≠ AWS real — relatório final declarará a restrição.
- Formatos de plano Spark variam por versão/fornecedor — parser precisa ser
  tolerante (ds-0013).
- Custo de APIs CloudWatch deve ser documentado e limitado por janelas.

## Contratos reutilizados

Todos os 7 contratos do Cycle 01 permanecem — evolução somente aditiva.
Nenhuma migração necessária.

## Plano de execução (specs)

ds-0011 (Glue connector) → ds-0012 (CloudWatch) → ds-0013 (plan analyzer) →
ds-0014 (join intelligence) → ds-0015 (SQL evolution) → ds-0016 (config
advisor) → ds-0017 (orchestrator+CLI+reporting) → ds-0018 (fixtures/E2E/
benchmarks) → ds-0019 (docs+final report). Ordem = dependências.

## Decisões de dependência registradas

- ADR 0008 — boto3 extra `[aws]` + API/MCP adiado para contratos/readiness.
- ADR 0009 — forma do connector protocol (sessão + allowlist + modelos
  internos).
