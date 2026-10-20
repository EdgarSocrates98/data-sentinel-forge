# Exemplo — Análise de plano físico

```bash
data-sentinel spark explain --file fixtures/plans/sort_merge_join.txt
```

Saída real (resumo — completa em `docs/evidence/cycle2/spark-explain.txt`):

```text
modo: offline
relatório 1f5d43f616134d8e8d657345e23551d9 (schema 1.0.0)
resumo: 3 achado(s): POSSIBLE=2, UNKNOWN=1
analyzers: join-intelligence-analyzer@0.1.0, spark-plan-analyzer@0.1.0

[LOW/POSSIBLE] cost
  Scan (nó 3) sem DataFilters declarados — leitura ampla. Pode ser
  intencional; se a query filtra em estágio posterior, avaliar predicate
  pushdown/partition pruning.
  evidência: fixtures/plans/sort_merge_join.txt:5
    [Scan] *(1) FileScan parquet [id#1L,name#4] Batched: true, ...

[MEDIUM/POSSIBLE] cost
  SortMergeJoin (nó 0) sem estatísticas declaradas no plano — o otimizador
  pode ter escolhido shuffle+sort sem cardinalidade confiável.
  validação: Coletar estatísticas (ANALYZE TABLE ... COMPUTE STATISTICS)
  validação: Medir bytes reais por lado via Spark UI
```

## Interpretando

- Nada é `CONFIRMED` aqui: plano estático não prova problema de execução.
- As limitações declaram exatamente o que falta (métricas de spill, skew,
  tempos de task) — e os passos de validação dizem como coletar.
- Para enriquecer: `EXPLAIN COST` traz estatísticas do otimizador; um
  descritor `--stats` traz cardinalidade declarada (ver
  `high-volume-joins.md`).

Outros fixtures para explorar: `cartesian.txt` (produto cartesiano
`CONFIRMED`), `aqe_initial.txt` (metadado AQE), `malformed.txt` /
`truncated.txt` / `unknown_operator.txt` (degradação honesta).
