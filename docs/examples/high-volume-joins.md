# Exemplo — JOINs em alto volume

Cenário E2E-E: SQL com 4 tabelas (230M, 73M, 230M, 250M linhas
**declaradas** no descritor — metadado sintético, nunca tabelas reais) e
estatísticas de chave indicando multiplicidade.

```bash
data-sentinel spark optimize \
  --sql fixtures/joins/high_volume_4tables.sql \
  --stats fixtures/joins/stats_4tables_m2m.json \
  --dialect spark
```

Saída real (resumo — completa em
`docs/evidence/cycle2/high-volume-joins.txt`):

```text
resumo: 7 achado(s): POSSIBLE=4, UNKNOWN=3

[HIGH/POSSIBLE] data_skew
  Risco de expansão many-to-many (sql-join-1: orders ⋈ customers).
  Quando ambos os lados podem ter múltiplas linhas por chave, a saída é o
  produto das multiplicidades por chave — crescimento intermediário pode
  exceder as entradas em ordens de magnitude.
  Evidência: chaves declaradas não-únicas.
  evidência: sql
    many-to-many risk orders ⋈ customers unicidade=known_non_unique/known_non_unique
  validação: SELECT k, COUNT(*) GROUP BY k HAVING COUNT(*)>1 em cada lado

[HIGH/POSSIBLE] data_skew
  Risco de expansão many-to-many (sql-join-2: junção-anterior ⋈ order_items)...
  validação: Coletar estatísticas de junção-anterior (expressão/subquery)
```

## Interpretando

- `orders ⋈ customers`: tabelas reais identificadas — passos `ANALYZE
  TABLE` válidos.
- `junção-anterior ⋈ order_items`: o lado esquerdo é o resultado composto
  do join anterior — não existe tabela para ANALYZE, então o passo é
  genérico ("coletar estatísticas da expressão/subquery").
- Status `POSSIBLE` mesmo com stats: unicidade não-única prova *risco*,
  não explosão confirmada — isso exigiria execução observada.
- Contraste com `stats_4tables_unique.json`: chaves únicas ⇒ fan-out
  `none`, sem alarme m2m.

## Descritor

`fixtures/joins/stats_4tables_m2m.json` declara `row_count` +
`keys.<col>.distinct` por tabela + `runtime` opcional para skew observado
(ver formato completo em `docs/guides/join-intelligence.md`).
