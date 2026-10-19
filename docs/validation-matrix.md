# Matriz de Validação — Cycle 01

Estados: `COMPLETE` / `PARTIAL` / `BLOCKED` / `NOT STARTED`. Toda evidência
aponta para arquivo real em `factory/runs/` ou `docs/evidence/` — nada aqui é
declarado sem comprovação.

## Por dimensão (§13)

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
