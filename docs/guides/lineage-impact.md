# Guia — Linhagem Operacional & Impacto

## Ingestão OpenLineage

```bash
data-sentinel lineage ingest --file marquez-real.jsonl
data-sentinel lineage ingest --file events.jsonl --json
```

Aceita JSONL (uma linha/evento), envelope `{"events":[...]}` ou evento
único. `eventType` runtime (START/RUNNING/COMPLETE/FAIL/ABORT) →
`LineageKind.OBSERVED`; flag `--declared`/ausência → STATIC.

O fixture `tests/fixtures/lineage/marquez-real.jsonl` foi **capturado de
um Marquez real** (Docker `marquezproject/marquez` + Postgres): eventos
POSTados em `/api/v1/lineage` (201) e confirmados via `/api/v1/jobs`.
Ver `PROVENANCE.json`.

## Grafo + Impacto

```bash
data-sentinel lineage impact \
  --file marquez-real.jsonl \
  --target s3://lakehouse-raw/raw/events
```

Saída: upstream/downstream transitivos (BFS), jobs afetados e a marca
obrigatória **"impacto POTENCIAL, não comprovado"** — o grafo prova
alcançabilidade, não quebra real.

## Limitações documentadas
- Linhagem de coluna preservada como facet bruto (`facets._raw_*`);
  o grafo de impacto opera em nível de dataset.
- Eventos malformados são contados em `rejected` + limitation, nunca
  descartados silenciosamente.
