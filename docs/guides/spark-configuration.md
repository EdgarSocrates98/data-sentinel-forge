# Guia — Spark Configuration Advisor

Recomenda configurações Spark a partir das propriedades atuais + sinais de
workload, com **matriz de compatibilidade por runtime** (Spark/Glue),
custos/impacto declarados e rollback — nunca um "confie em mim".

## Instalação

Core, offline total.

## Uso

```bash
# sozinho (via python/api) ou composto no pipeline:
data-sentinel spark optimize \
  --sql query.sql \
  --config spark-defaults.conf \
  --stats stats.json
```

O arquivo `--config` aceita `chave=valor` por linha (formato
`spark-defaults.conf` / `--conf` / argumentos de job Glue
`--conf`/`Spark properties`).

## Matriz de compatibilidade

Propriedades cobertas (ver `analyzers/spark/config/matrix.py`):

`spark.sql.adaptive.enabled` · `spark.sql.shuffle.partitions` ·
`spark.sql.autoBroadcastJoinThreshold` ·
`spark.sql.adaptive.coalescePartitions.enabled` ·
`spark.sql.adaptive.skewJoin.enabled` · `spark.sql.files.maxPartitionBytes`
· `spark.executor.memory` · `spark.executor.cores` · `spark.driver.memory` ·
`spark.dynamicAllocation.enabled` · `spark.sql.cbo.enabled`

Cada recomendação declara a versão mínima de runtime em que a propriedade
faz sentido — propor `adaptive.*` para Spark 2.x seria inválido e a matriz
o impede.

## O que uma recomendação contém

- `target`: a propriedade e valor proposto.
- `observed`: config atual (ou "ausente — default implícito").
- `evidence` + `reasoning`: por que, ancorado no que foi visto.
- `proposed experiment`: como testar em ambiente controlado.
- `expected benefit`: **hipótese** declarada como tal.
- `risks`, `validation`, `rollback`: incluindo implicação de
  custo/disponibilidade quando o alvo é recurso (memória/cores).

## Sinais de contexto

O advisor lê sinais passados pelo orquestrador via `ExecutionContext.extra`
(chaves `workload_*`: OOM evidence, skew, volume de shuffle, contagens de
join/exchange). Achados de outros analyzers chegam como metadado do
request — nunca por import direto entre analyzers.

## Limitações

- Sem evidência de workload, recomendações ficam genéricas e de baixa
  confiança — ou ausentes.
- Valores sugeridos são pontos de partida para experimento, não
  prescritos: a seção `validation` diz o que medir antes/depois.
- Glue tem defaults próprios (ex.: AQE on por padrão no Glue 3+); o
  advisor considera o runtime declarado em `--platform`.

## Problemas comuns

| Sintoma | Ação |
|---|---|
| nenhuma recomendação | config já coerente ou sem evidência — ambos os casos são declarados |
| recomendação ignorada no runtime | versão abaixo do mínimo da propriedade — a matriz já filtra; confira `--platform` |
