# Guia — Análise de Planos Físicos Spark

Parser tolerante de saídas `EXPLAIN`/`df.explain()` que monta a árvore de
operadores, detecta estratégias de join, shuffles, metadados AQE e gera
achados **com spans de evidência** — e limitações quando a evidência não
existe.

## Instalação

Nenhuma dependência extra — funciona no pacote core, **100% offline**.

## Uso

```bash
# gerar o plano no Spark
spark-sql -e "EXPLAIN EXTENDED SELECT ..." > plano.txt
# ou df.explain(True) / EXPLAIN COST

data-sentinel spark explain --file plano.txt
data-sentinel spark explain --file plano.txt --json --output plano-report.json
```

Formatos reconhecidos (auto-detect): `== Physical Plan ==` (df.explain),
planos com `Statistics` (EXPLAIN COST), formato `(N)` de
`EXPLAIN FORMATTED`, e blocos `Parsed/Optimized Logical Plan`. Marcadores
de stage `*(1)` e prefixos de árvore `+-`, `:-`, `|` são reconhecidos.

## O que o analyzer enxerga

- **Árvore de operadores** com `node_id`, pai/filhos, span de linhas no
  arquivo-fonte e `raw_text` preservado.
- **Joins**: `SortMergeJoin`, `BroadcastHashJoin`, `ShuffledHashJoin`,
  `BroadcastNestedLoopJoin`, `CartesianProduct` — o último gera
  `HIGH/CONFIRMED` (produto cartesiano é fato sintático, não hipótese).
- **Exchanges/shuffles**: `Exchange hashpartitioning`, `Repartition`,
  `Coalesce` — sinalizados como custo de investigação, não como problema
  automático.
- **AQE**: `AdaptiveSparkPlan isFinalPlan=...` registrado como metadado.
- **Estatísticas declaradas**: `sizeInBytes`, `rowCount` extraídos e
  marcados como `estimated` (estimativa do otimizador — nunca confundida
  com métrica observada).
- **Operadores desconhecidos**: preservados como `unknown:<nome>` +
  warning, nunca descartados silenciosamente.

## Interpretação

- `POSSIBLE` em scans sem `DataFilters`/`PartitionFilters`: leitura ampla
  *pode* ser intencional — a validação sugerida é medir partições lidas.
- `POSSIBLE` em SortMergeJoin sem estatísticas: candidato a broadcast é
  hipótese, confirmável só com tamanhos reais.
- A seção `limitações` declara explicitamente: plano estático ≠ execução
  (sem spill, sem skew observado, sem tempos de task).

## Limitações honestas

- Plano truncado/malformado → limitação, não estrutura inventada.
- Sem event log ou métricas, não há como afirmar skew/spill/tempo.
- Cardinalidade **nunca** é derivada de row counts sozinhas — exige
  estatísticas de chave declaradas (ver `join-intelligence.md`).

## Problemas comuns

| Sintoma | Ação |
|---|---|
| "nenhum operador identificado" | confira se o arquivo é texto `EXPLAIN`, não binário/event log JSON |
| muitos `unknown:` | operadores de vendors (Photon, Gluten) — preservados; contribua ao `KNOWN_OPERATORS` |
| findings só `UNKNOWN` | esperado quando falta estatística — o relatório diz o que coletar |

## Evidência adicional

Combine com `--stats` em `spark optimize` (descritor JSON com
`row_count`/`keys`/`top_keys` declarados) ou com o plano `EXPLAIN COST`
(que já traz estatísticas do otimizador).
