# Cycle 09 — Contract Convergence & Foundation Report

**SHA:** `146c9d3` (foundation) + follow-up (this commit)
**Data:** 2026-10-26 · **Modo:** dynamic loop, prompt_evo_cycle9.md

## Escopo executado

| Gap | Status | Evidência |
|---|---|---|
| G-01 multi-input tools inalcançáveis via API | **FIXED** | `POST /api/v1/analyze/{id}` valida o body inteiro contra `inputSchema` do tool (required → 400, type → 422); chaves `file`/`*_file`/`*_path`/`*_bundle`/`*_report` resolvidas sob `allowed_roots` + extensão permitida; `allowed_roots` propagado ao `execute_tool`. `detect_drift`, `lineage.impact`, `doctor.correlate`, `emr.estimate_cost` agora callable. Contrato v1 `{"file"}` preservado |
| G-02 plan tree não tipado | **FIXED** | `PlanNode/ExecutionPlan.to_dict()` = wire shape JSON-safe; `spark.analyze_plan` emite `plan`; `extractPlanTree` no Angular reconstrói a árvore de operadores (fallback legado mantido) |
| G-03 TS contracts não validados | **FIXED** | `tests/contract/test_ts_contract_parity.py` — parseia `api.models.ts` e compara field names contra `model_fields`/dataclasses/endpoint keys (8 interfaces: Health, Capability, ToolManifest, Snapshot, QualityObservation, RemediationPlan, PlanNodeWire, ExecutionPlanWire) |
| G-04 persistência | **FIXED** | `PRAGMA busy_timeout=5000` nos 3 stores; schema v2 com `ingestion_checkpoints` (cursor resumable p/ Cycle 10); migração v1→v2 testada sem perda; retention `prune` já existia e segue coberta |
| G-05 error taxonomy/trace IDs | **FIXED** | middleware `X-Request-Id` (honra inbound, minta `token_hex(8)`, cobre até rejeições de guard); handlers `SentinelError`→envelope `{detail, code, details, request_id}` com status por classe; `HTTPException`→`{detail, request_id}`; catch-all 500 redacted |

## Verificação reproduzível

```
.venv/bin/python -m pytest --tb=short -q   → 1052+ passed, 4 env-gated skips
.venv/bin/ruff check src tests             → clean
.venv/bin/mypy                             → 0 issues / 163 arquivos
uv build                                   → wheel + sdist OK
frontend: npx ng test                      → 97/97 specs
install smoke: wheel em venv isolada       → `data-sentinel capabilities --descriptors` offline → 15 capabilities, zero rede
```

## Gate Cycle 09 (supported surfaces × contracts × tests)

| Tool | CLI | MCP | API | Contrato | Teste real |
|---|---|---|---|---|---|
| spark.analyze_plan | ✓ | ✓ | ✓ (com `plan` tipado) | inputSchema `file` | `test_analyze_plan_returns_typed_tree` |
| quality.detect_drift | ✓ | ✓ | ✓ (2 arquivos) | `baseline_file+current_file` | API + registry |
| lineage.impact | ✓ | ✓ | ✓ (file+target) | `file+target` | API + registry |
| doctor.correlate | ✓ | ✓ | ✓ (2 arquivos) | `doctor_bundle+sentinel_report` | registry + schema |
| emr.estimate_cost | ✓ | ✓ | ✓ (sem file) | `platform`+numéricos | API |

Demais 16 tools single-file: sem mudança de contrato, caminho v1 intacto.

## Não executado / limitações

- Angular build (`ng build`) e Playwright e2e não rodados neste tick — `frontend.yml` CI é a referência; specs unitários verdes.
- Cycle 10–15 não iniciados — gates anteriores passam agora; event-log streaming Spark Autopsy é o próximo bloco.
- `ingestion_checkpoints` é plumbing (tabela+CRUD+testes); consumidores chegam no Cycle 10.

## Riscos residuais

- `analyze` aceita inputs arbitrários por schema — o schema é a fronteira; novos tools precisam declarar `inputSchema` completo.
- TS parity cobre 8 interfaces críticas; payload shapes aninhados (Finding, Evidence) ainda confiam em testes de endpoint existentes.
