# Cycle 03 — Baseline Audit

Auditoria da `main` antes do Cycle 03, conforme §1 do `prompt_evo_cycle3.md`.

## SHA auditado

`90c10a8b703a67b7ced408e86992b71a16765ce4` — HEAD da `main` resolvido em
tempo real (confere com a referência do prompt; não presumido).

## Verificação executada agora

| Comando | Resultado |
|---|---|
| `uv sync --extra dev` | resolvido — 46 pacotes |
| `uv run ruff check src tests` | All checks passed |
| `uv run mypy src` | 78 arquivos, 0 issues (strict) |
| `uv run pytest -q` | **360 passed, 1 skipped** (~5.5s) |
| `uv build` | wheel + sdist `data_sentinel-0.1.0` |
| `data-sentinel version` | `data-sentinel 0.1.0` |
| `data-sentinel doctor` | todos os checks PASS, 6 analyzers |
| `pytest --cov` (referência Cycle 02) | 88% — comparar ao final |

Baseline documental do Cycle 02: 360 testes / 1 skipped / 88% cobertura —
**os números batem** com a nova execução.

## CI remota (§1.3)

- SHA: `90c10a8` — workflow `CI`, 6 jobs (ubuntu/windows/macos × py3.11/3.12).
- Status real: **failure — jobs nunca iniciaram**. Anotação do run
  `39351536029`: *"job was not started because recent account payments
  have failed or your spending limit needs to be increased."*
- Causa: repo **privado** → minutos de Actions cobrados; conta com
  billing pendente. Não é falha de código — os mesmos comandos passam
  localmente (acima).
- Opções registradas: ajustar billing ou tornar o repo público.

## Restrições herdadas (§1.4) — mantidas visíveis

- **AWS real**: código validado com mocks/Stubber; teste real env-gated
  `DATA_SENTINEL_AWS_TESTS=1` skipped por padrão.
- **Credenciais AWS**: *não presentes neste ambiente* (sem `~/.aws`, sem
  env vars, `boto3.Session().get_credentials() → None`). Decisão do grill
  "tentar AWS real" ⇒ se não surgirem credenciais até ds-0028, homologação
  real = **BLOCKED** (§12 prevê isso). Account ID fornecido pelo usuário:
  `702561771161` (usado em contextos de exemplo/guia).
- **API/MCP**: contratos + readiness apenas — sem servidor.
- **Windows/macOS**: só via CI — que está bloqueada por billing.
- **Cobertura**: 88% (>85% piso) — acompanhar.

## Evolução de contratos feita neste spec (aditiva — schema 1.0.0)

- Enums: `SupportStatus` (SUPPORTED/WITH_CONSTRAINTS/UNSUPPORTED/UNKNOWN/
  NOT_VERIFIED — "não verificado" ≠ "não suportado"), `FindingCategory.
  COMPATIBILITY`, `SourceType.{ICEBERG_METADATA,POLICY_DOC,ACCESS_CONTEXT}`.
- `core/contracts/lakehouse.py`: `IcebergTableMetadata`,
  `IcebergSnapshotSummary`, `AccessContext`, `CompatibilityAssessment`,
  `LakehouseOperation` — exportados + schemas gerados.
- Scaffolding: `analyzers/iceberg/`, `knowledge/` (+`knowledge/rules/`
  package-data para YAML empacotado no wheel).
- ADR 0011: knowledge rules YAML + novos conectores read-only+simulate.

## Plano de specs (ordem = dependências)

ds-0021 (Iceberg) → ds-0022 (knowledge base) → ds-0023 (compat engine,
consome ds-0022) → ds-0024 (cross-account) → ds-0025 (IAM/S3/KMS) →
ds-0026 (MERGE/APPEND) → ds-0027 (resolver+CLI+reporting) → ds-0028
(fixtures/security/E2E + tentativa AWS real) → ds-0029 (docs+relatório).
