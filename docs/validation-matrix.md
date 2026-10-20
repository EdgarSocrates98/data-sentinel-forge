# Matriz de Validação — Cycles 01 + 02

Estados: `COMPLETE` / `PARTIAL` / `BLOCKED` / `NOT STARTED`. Toda evidência
aponta para arquivo real em `factory/runs/` ou `docs/evidence/` — nada aqui é
declarado sem comprovação.

## Por dimensão (§13) — Cycle 02

| Dimensão | Estado | Evidência |
|---|---|---|
| Funcional | COMPLETE | `pytest -q` → 360 passed, 1 skipped — `factory/runs/ds-0019.verification.log` |
| Contrato | COMPLETE | `tests/contract` 9/9; evolução aditiva (`SourceType`, `duration_ms`, `recommendations`), schema 1.0.0 |
| Segurança | COMPLETE | `tests/security/` 55 testes — hostis em plano/SQL/stats/AWS + allowlist + regex quadrático corrigido |
| CLI | COMPLETE | Grupos `glue/spark/sql/report` + legado; saídas reais em `docs/evidence/cycle2/` |
| Compatibilidade | COMPLETE | CI matrix 3 SO × 2 Pythons; local em 3.12 — outros ambientes só via CI |
| Performance | COMPLETE | `docs/evidence/benchmarks.json` — números medidos com metadados de máquina |
| Documentação | COMPLETE | `docs/guides/` (6), `docs/examples/` (3), `docs/cycles/` (4) — comandos spot-checked |
| Integração | COMPLETE | `tests/integration` 34 + `tests/e2e` A–E 6 cenários |
| Regressão | COMPLETE | Suite verde a cada spec — `factory/runs/ds-00XX.verification.log` |
| CI | COMPLETE | Workflow cobre suite inteira (`pytest -q` inclui golden/security/e2e/bench) |
| AWS real | PARTIAL | **Validado com mocks/Stubber, não AWS real** — teste real env-gated `DATA_SENTINEL_AWS_TESTS=1` |
| API/MCP | PARTIAL | Contratos + readiness apenas (decisão Grill Gate) — sem servidor |

## Por funcionalidade — Cycle 02

| Funcionalidade | Estado | Evidência |
|---|---|---|
| Glue connector read-only | COMPLETE | `connectors/aws/glue.py` + Stubber tests — `factory/runs/ds-0011.verification.log` |
| CloudWatch logs + correlação + timeline | COMPLETE | `analyzers/cloudwatch/`, `diagnostics/` — `factory/runs/ds-0012.verification.log` |
| Spark plan analyzer | COMPLETE | `analyzers/spark/plans/` — `factory/runs/ds-0013.verification.log` |
| Join intelligence/cardinalidade | COMPLETE | `analyzers/spark/joins/` + `fixtures/joins/` — `factory/runs/ds-0014.verification.log` |
| SQL analyzer v0.2 (AST/dialetos) | COMPLETE | `analyzers/sql/` — `factory/runs/ds-0015.verification.log` |
| Spark config advisor | COMPLETE | `analyzers/spark/config/` — `factory/runs/ds-0016.verification.log` |
| Orquestrador + CLI grupos + Markdown | COMPLETE | `diagnostics/orchestrator.py`, `reporting/`, CLI — `factory/runs/ds-0017.verification.log` |
| Golden/security/benchmarks/E2E | COMPLETE | `tests/{golden,security,benchmarks,e2e}/` — `factory/runs/ds-0018.verification.log` |
| Docs + relatório final | COMPLETE | este documento + `docs/cycles/` |

## Por dimensão (§13) — Cycle 01

| Dimensão | Estado | Evidência |
|---|---|---|
| Funcional | COMPLETE | `pytest -q` → 168 passed — `docs/evidence/pytest.txt` |
| Contrato | COMPLETE | `schemas/*.schema.json` exportados + `tests/contract/test_json_schemas.py` valida schema↔modelo e round-trip JSON |
| Segurança | COMPLETE | `tests/security/test_security.py` — traversal, symlink, NUL, oversize, binário, redação +/−, marcadores |
| CLI | COMPLETE | Comandos reais em `docs/evidence/` (`analyze-glue-oom.txt`, `analyze-sql.json`, `doctor.txt`, `capabilities.txt`, `config-show.txt`) |
| Compatibilidade | COMPLETE | `.python-version` 3.12; CI matrix Ubuntu/Windows/macOS × 3.11/3.12 (`.github/workflows/ci.yml`) — validada localmente em 3.12; outros ambientes validados apenas via CI |
| Performance | PARTIAL | Não medido — nenhum benchmark é afirmado; suite completa roda em ~1s (`pytest.txt`) |
| Documentação | COMPLETE | `examples/README.md` + saídas reais em `docs/evidence/` |
| Integração | COMPLETE | `tests/integration/test_cli.py` — 25 testes CLI fim-a-fim incluindo persistência round-trip |
| Regressão | COMPLETE | Suite completa verde em cada spec; logs em `factory/runs/ds-000{1..8}.verification.log` |
| CI | COMPLETE | Workflow configurado (`.github/workflows/ci.yml`); resultado local idêntico aos comandos do CI |

## Por funcionalidade entregue

| Funcionalidade | Estado | Evidência |
|---|---|---|
| Pacote instalável (src-layout, hatchling) | COMPLETE | `pip/uv install` + `data-sentinel version` — `factory/runs/ds-0001.verification.log` |
| Contratos públicos versionados | COMPLETE | `core/contracts/*` + `schemas/` + testes de contrato |
| Config com precedência documentada | COMPLETE | `core/configuration/*` + `tests/unit/test_config.py` |
| Path guard + redação + sanitização | COMPLETE | `core/security/*` + `tests/security/` |
| Analyzer Spark/Glue (9 classes de padrão) | COMPLETE | `analyzers/spark/*` + `tests/unit/test_log_analyzer.py` + fixtures por padrão |
| Analyzer SQL estático (8 checks, dialetos) | COMPLETE | `analyzers/sql/*` + `tests/unit/test_sql_analyzer.py` |
| Persistência SQLite + migrations | COMPLETE | `persistence/*` + `tests/unit/test_store.py` |
| CLI completa (6 comandos) | COMPLETE | `cli/__init__.py` + `tests/integration/test_cli.py` |
| Diagnóstico real reproduzível | COMPLETE | `docs/evidence/analyze-glue-oom.txt` |
| Relatório JSON válido | COMPLETE | `docs/evidence/analyze-sql.json` |
| ADRs arquiteturais | COMPLETE | `docs/adr/0001..0007` |
| Conectores cloud (Glue/CloudWatch) | NOT STARTED | Cycle 02 — fora do escopo deste ciclo |
| API / MCP / agentes | NOT STARTED | Cycles 02–05 — pacotes placeholder existem sem implementação |
