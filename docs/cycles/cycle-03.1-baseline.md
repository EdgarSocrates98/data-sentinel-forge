# Cycle 03.1 Baseline

Baseline SHA (data-sentinel-forge): `7510b7557fb9d78b7116522a6236ea1be25a6408`
(HEAD após Cycle 03, push `90c10a8..7510b75`).

Repos auditados (read-only nesta execução):
- forge-doctor-data: `266e789a3f2da850fa667236cc6b44d0fc22bd61`
- forge-doctor-api: `8912f3b233f6710c57908f1b92cfe25eb9478d62`

## Data Sentinel (estado de entrada)

- Pacote `data-sentinel`, src-layout, hatchling+uv, Python 3.12.
- 93 arquivos src, 32 arquivos de teste, 488 testes, 3 skips env-gated.
- 10 analyzers: cloudwatch, cost, crossaccount, glue, iam, iceberg,
  lakeformation, operations, quality, spark/sql.
- Contratos Pydantic v2 `schema_version` 1.0.0 + domínio lakehouse (Cycle 03).
- Knowledge base: 8 regras YAML empacotadas (`knowledge/rules/`).
- CLI `data-sentinel`: analyze/report/doctor/capabilities/config/glue/spark/
  sql/lakehouse/report-show + import paths.
- Store SQLite stdlib; orquestrador determinístico; renderers terminal/JSON/
  Markdown; contratos API/MCP (readiness, sem servidor).
- `doctor` PASS: python, config, store, 10 analyzers, redação ativa.
- CI remota: bloqueada por billing (repo privado); equivalentes locais verdes.
- AWS real: BLOCKED sem credenciais; allowlist read-only verificada.

## Restrições herdadas

- Windows/macOS só via CI. API/MCP contratos apenas. Sem credenciais AWS.
