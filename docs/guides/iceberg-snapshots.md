# Guia — Snapshots Iceberg

O analyzer lê a lista `snapshots` do metadata.json: id, parent, timestamp,
operation, sequence-number, summary, manifest-list.

## Análises

- Cadeia: parent do snapshot atual ausente → evidência de expiração ou
  coleta parcial (confiança reduzida).
- Operações agregadas por tipo (append/overwrite/replace/delete) —
  declarado, não observado.
- Summaries: `added-data-files`, `deleted-data-files`,
  `added-files-size` alimentam o diagnóstico condicional de small files.
- `snapshot-log` >20 entradas → custo de listagem.
- `refs` (branches/tags) reportados em metadata do resultado.

## Interpretação correta

Snapshot metadata é **estado declarado do catálogo**. Latência real de
commit, throughput e skew NÃO aparecem aqui — para isso use plano/event
log/CloudWatch (analyzers Spark/Glue).
