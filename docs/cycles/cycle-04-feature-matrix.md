# Cycle 04 — Feature Matrix

| Área | Entregue | Evidência |
|---|---|---|
| Contratos de qualidade versionados | `DataQualityContract` + parser §3.2 YAML/JSON | `core/contracts/quality.py`, `quality/contract.py`, JSON schemas |
| Validação estática | dup ids, severidade, ratio [0,1], target×schema, version check | `quality/contract.py`, `quality/versioning.py` |
| Adapters de resultados | PyDeequ, Deequ checks, Great Expectations, SQL rows, DataFrame export | `quality/adapters.py` — parse-only (Grill Gate) |
| Missing != pass | falha/ausência → UNKNOWN | testes unit/e2e |
| Profiling | ColumnProfile: count/nulls/distinct/min/max/mean/std/p50/p95/hist/top-k | `quality/profile.py` (numpy ou stdlib) |
| Drift | KS test (scipy) / PSI + TV heurístico com limitation | `quality/drift.py`, extra `stats` |
| Linhagem OpenLineage | JSONL/batch/single, run + column lineage, OBSERVED vs STATIC | `lineage/openlineage.py` + fixture REAL Marquez |
| Grafo + impacto | BFS upstream/downstream, potencial_only=True | `lineage/graph.py` |
| Interop export | DiagnosticReport → bundle forge-contracts/1 + sha256 | `adapters/doctor/exporter.py` + round-trip |
| CLI | `quality validate|import`, `lineage ingest|impact`, `report export` | `cli/__init__.py` |
| Segurança | safe_load only, caps, no-eval, offline provado | `tests/security/test_security_cycle4.py` |
| E2E | A–H | `tests/e2e/test_quality_e2e.py` |
| Benchmarks | números reais | `docs/evidence/benchmarks-cycle4.json` |

## Não entregue / limitações honestas
- Engines de qualidade não são executados (só parse de exportações).
- Sem scipy instalado, drift cai para heurística declarada no resultado.
- Impacto = alcançabilidade no grafo (potencial), nunca prova de quebra.
- Linhagem de coluna preservada como facet bruto; impacto coluna-a-coluna
  não filtra o grafo de datasets.
- CI remota segue bloqueada por billing (repo privado).
