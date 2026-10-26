# Pre-Cycle-09 Baseline Audit

**SHA:** `7b62c8134df8dc0e354e4309efab64a0705eb21a` (main, `Merge pull request #2 — release/0.3.0-minor`)
**Data:** 2026-10-26
**Auditor:** Devin (loop tick 1, prompt_evo_cycle9.md)
**Working tree:** clean no início da auditoria (`dist/` rebuildado durante ela — artefato de build, não fonte)

## Baseline checks — comandos e resultados

| Check | Comando | Resultado |
|---|---|---|
| pytest | `.venv/bin/python -m pytest --tb=short -q` | **1045 passed, 4 skipped** (73s). Skips são env-gated: `test_lakehouse_e2e`, `test_scenarios`, `test_emr_security`, `test_security_cycle3` — todos exigem credenciais AWS non-prod reais |
| ruff | `.venv/bin/ruff check src tests` | **All checks passed** (0 findings, rules E/F/W/I/UP/B/SIM/RUF/S/A/C4/DTZ/T20/PTH) |
| mypy strict | `.venv/bin/mypy` | **0 issues em 163 arquivos** (strict + pydantic plugin) |
| build | `uv build` | **OK** — `data_sentinel-0.3.0-py3-none-any.whl` (325 KB) + `.tar.gz` (523 KB) |
| MCP handshake | `initialize` + `tools/list` via stdio | **OK** — protocol 2024-11-05, 21 tools registradas |
| CLI smoke | `data-sentinel --help` / `capabilities --descriptors` | **OK** — 18 command groups, descriptors JSON completos com limitations |
| Angular | não rodado neste tick (node_modules presente; `frontend.yml` CI cobre build/test/e2e) | DEFERRED |
| Playwright | não rodado neste tick (frontend/test-results e playwright-report existem de runs anteriores) | DEFERRED |
| schemas | `schemas/` dir presente; validação coberta por jsonschema nos testes | OK (via pytest) |
| benchmarks | pytest-benchmark instalado; `docs/evidence/benchmarks*.json` de ciclos anteriores | NOT_RUN neste tick |

## Capability inventory

Superfícies registradas e conferidas em código (não em docs):

| Capacidade | Estado | Evidência |
|---|---|---|
| Analyzer registry + `run_diagnostics` orchestrator | IMPLEMENTED | `analyzers/registry.py`, `diagnostics/orchestrator.py` |
| Tool registry (21 tools) + `execute_tool` com budget/truncation | IMPLEMENTED | `tools/registry.py`; MCP `tools/list` live |
| MCP stdio server | IMPLEMENTED | `mcp_server.py` + handshake real |
| FastAPI Control Center (auth, rate-limit, CORS, SSE, audit) | IMPLEMENTED | `api/app.py` — SessionAuth com TTL/rotação/revogação, host/origin guards, payload limit, token bucket |
| Investigations + SSE stream + persistence SQLite | IMPLEMENTED | `persistence/investigations.py`, migrations `0001_init.sql` |
| Snapshots/watches/alerts/remediation plans | IMPLEMENTED | `persistence/operations.py` + endpoints `/api/v1/*` |
| Spark plan parser + analyzer (findings com provenance) | IMPLEMENTED | `analyzers/spark/plans/*` — **mas plan tree NÃO é saída tipada** (ver gaps) |
| Quality contracts/drift/normalize | IMPLEMENTED | `quality/*`, tools `quality.assess`/`quality.detect_drift` |
| Lineage OpenLineage ingest + impact | IMPLEMENTED | `lineage/*`, tools `lineage.ingest`/`lineage.impact` |
| EMR (ec2/serverless/eks) + cost estimate | IMPLEMENTED | `analyzers/emr/*` |
| Glue/CloudWatch/IAM/LakeFormation/Iceberg analyzers | IMPLEMENTED | `analyzers/*` |
| Doctor adapter (import/correlate) | IMPLEMENTED | `adapters/doctor/*` |
| Angular Control Center | IMPLEMENTED | `frontend/src/app` — investigations, evidence-graph, operations, quality-lineage, spark-plans |
| Instalação multi-host (claude/devin/codex/copilot + cursor parcial) | IMPLEMENTED | `installation/*`, `forge.json`, `forge.agentic.json` |
| Contrato TS do frontend | PARTIAL | `frontend/src/app/core/api.models.ts` é **hand-maintained**, sem geração/validação contra o backend |
| Spark Autopsy (event-log ingestion, task/executor correlation) | MISSING | Cycle 10 |
| Data Explorer (catalog metadata discovery) | MISSING | Cycle 12 |
| API analyze endpoint multi-input | **BLOCKED/BUG** | ver G-01 |

## Gaps confirmados em código (Cycle 09 targets)

**G-01 — `/api/v1/analyze/{analyzer_id}` não suporta tools multi-input.** `app.py::analyze` exige `body["file"]` e chama `execute_tool(input={"file": p})`. Tools que exigem outros inputs falham ou nunca recebem os dados:
- `sentinel.quality.detect_drift` → `baseline_file` + `current_file` (KeyError garantido)
- `sentinel.lineage.impact` → `file` + `target` (KeyError)
- `sentinel.doctor.correlate` → `doctor_bundle` + `sentinel_report` (KeyError)
- `sentinel.emr.estimate_cost` → `platform` + numéricos, **sem file** (sempre 400 "file is required")
Também: o endpoint não valida inputs contra `input_schema` e não usa `allowed_roots` no `execute_tool`.

**G-02 — Plan tree não é output tipado.** `SparkPlanAnalyzer` constrói `ExecutionPlan` (dataclass com nodes/roots/stats_provenance) mas o tool retorna só findings; o tree não é serializado nem exposto. Cycle 09 pede "structured Spark plan trees as typed outputs".

**G-03 — TS contracts não gerados.** `api.models.ts` espelha o backend manualmente; drift silencioso possível. Cycle 09 pede generated/validated TS contracts.

**G-04 — Migrações mínimas.** Só `0001_init.sql`; Cycle 09 pede hardening (retention, concurrency, recovery/rollback tests, ingestion checkpoints).

**G-05 — Error taxonomy/trace IDs.** `ApiError` existe mas endpoints usam `HTTPException(detail=...)` heterogêneo; sem `request_id`/trace propagation padronizado.

## Limitações desta auditoria

- AWS-dependent paths (Glue/EMR/Athena live) não exercidos — sem credenciais; connectors são read-only e export-driven por design.
- Angular build/Playwright deferidos para tick seguinte (CI `frontend.yml` é a fonte de verdade atual).
- Inventory cobre superfícies exercitáveis offline; capabilities marcados IMPLEMENTED passam nos 1045 testes.
