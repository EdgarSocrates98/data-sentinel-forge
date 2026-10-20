# Incident Evidence Graph

`data_sentinel.diagnostics.incident` constrói um grafo operacional por
incidente a partir de um `UnifiedExecutionContext` + findings + evidence.

## Contexto unificado

`UnifiedExecutionContext` tem 16 campos (account, region, job_name,
run_id, runtime, glue/spark/iceberg versions, catalog, database, table,
log_stream, stage_id, task_id, timestamp, operation, execution_status).
Campo ausente permanece UNKNOWN (string vazia) — nunca inventado.

## Nós (10) e arestas (9)

Nós: JobRun, LogEvent, SparkStage, SparkTask, Table, Catalog, Snapshot,
IAMPrincipal, PermissionFinding, DiagnosticFinding.

Arestas: EXECUTED_AS, PRODUCED, FAILED_AT, REFERENCED, READ_FROM,
WROTE_TO, ASSOCIATED_WITH, SUPPORTED_BY, POTENTIALLY_CAUSED_BY.

## Regras de ouro

1. **Toda aresta exige `justification`** — a chave compartilhada que
   legitima o vínculo (ex.: `run_id=jr_1`, `table=orders`). Aresta sem
   justificativa é recusada e registrada em `limitations`.
2. **Correlação ≠ causalidade.** `causal_edges()` retorna apenas
   POTENTIALLY_CAUSED_BY — e mesmo essas são *potenciais*, jamais prova.
3. **Findings importados** (Doctor) recebem somente arestas de associação
   — nunca causais — e `attrs["imported"]=True`.
4. Arestas para nós inexistentes são descartadas com limitação explícita.

## Timeline multi-fonte

`build_timeline()` produz entradas com timestamps REAIS observados
(nunca sintetizados), classificadas por `EventKind`. `detect_gaps()`
declara intervalos >120s sem eventos. `merge_timelines()` funde fontes
declarando granularidades em `granularity_notes`.

```python
from data_sentinel.diagnostics.incident import (
    UnifiedExecutionContext, build_incident_graph)
from data_sentinel.diagnostics.timeline import build_timeline, merge_timelines
```
