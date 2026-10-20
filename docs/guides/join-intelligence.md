# Guia — Join Intelligence & Cardinalidade

Raciocínio sobre risco de cardinalidade em joins a partir de SQL/plano +
estatísticas **declaradas**. A regra de ouro: `UNKNOWN` vence inventado —
sem estatísticas de chave, nenhuma cardinalidade é afirmada.

## Instalação

Core, offline total. O input extra é um descritor JSON de estatísticas.

## Descritor de estatísticas

```json
{
  "tables": {
    "orders": {
      "row_count": 230000000,
      "keys": {"customer_id": {"distinct": 45000000, "source": "declared"}},
      "top_keys": [{"key": "0", "fraction": 0.22}]
    },
    "customers": {
      "row_count": 73000000,
      "keys": {"customer_id": {"distinct": 73000000}}
    }
  },
  "runtime": {
    "stage_12": {"task_time_p50_ms": 800, "task_time_p99_ms": 21000}
  }
}
```

`runtime` carrega métricas **observadas** (durações de task) — o analyzer
nunca fabrica esses valores; se não vêm no descritor, skew fica no máximo
"suspeito".

## Uso

```bash
data-sentinel spark optimize \
  --sql fixtures/joins/high_volume_4tables.sql \
  --stats fixtures/joins/stats_4tables_m2m.json \
  --dialect spark
```

Roda o pipeline composto: SQL estático → extração do grafo de joins →
avaliação de cardinalidade → sinais de skew. (`--config` aceita ainda um
arquivo de propriedades Spark para o advisor — ver `spark-configuration.md`.)

## O que o analyzer distingue

- **Formas de join**: INNER, LEFT, RIGHT, FULL, CROSS, SEMI, ANTI,
  multi-chave, expressão e desigualdade — via AST, não regex.
- **Many-to-many**: quando *nenhum* lado tem unicidade conhecida, a saída
  pode ser produto de multiplicidades → `HIGH/POSSIBLE` com a base de
  evidência declarada ("unicidade desconhecida" vs "chaves declaradas
  não-únicas").
- **Skew suspeito vs observado**: `top_keys` com fração ≥10% ⇒ SUSPEITO
  (inferência estática); `task_time_p99/p50 ≥ 5×` ⇒ OBSERVADO (evidência
  operacional real). A métrica de stage sinaliza o estágio — não identifica
  a chave.
- **Falta de evidência**: `LOW/UNKNOWN` listando exatamente o que falta
  (`row_count`, `distinct` por chave) e como coletar (`ANALYZE TABLE …`
  para tabelas reais; passo genérico para subqueries/lados derivados).

## Limites declarados (sempre no relatório)

- Deduplicação **nunca** é sugerida automaticamente — altera resultados
  funcionais e exige decisão humana.
- Cardinalidade real nunca é derivada só de `row_count` — unicidade de
  chave é o que determina fan-out.
- Recomendações vêm como hipóteses com riscos, validação e rollback.

## Problemas comuns

| Sintoma | Ação |
|---|---|
| "descritor de estatísticas inválido" | JSON malformado — valide com `jq .` |
| muitos `UNKNOWN` | normal sem stats — o relatório diz o que coletar |
| join plan-side com `unknown` | plano não expõe nomes de tabela — supra via `--sql` |
