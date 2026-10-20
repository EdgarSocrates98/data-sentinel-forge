# Guia — Análise Estática de SQL

Analyzer baseado em **AST SQLGlot** (não regex) com dialetos explícitos
Spark e Trino/Presto/Athena. Detecta anti-padrões com contexto — e sabe
quando *não* acusar.

## Instalação

Core (sqlglot já é dependência). Offline total.

## Uso

```bash
data-sentinel sql analyze --file query.sql --dialect spark
data-sentinel sql analyze --file query.sql --dialect trino   # Athena/Presto
data-sentinel sql analyze --file query.sql --json
```

`--dialect` é explícito e fica registrado nos metadados do relatório:
Athena/Trino **não** é tratado como Spark — sintaxe específica de engine
(`approx_distinct`, `UNNEST`, tipos) é parseada no dialeto certo.

## Checks (v0.2.0)

| Check | Contexto |
|---|---|
| `SELECT *` | **não** acusa dentro de `EXISTS (...)`, `COUNT(*)`, wrappers semânticos — só projeção ampla real |
| Join sem predicado | `JOIN` com `ON TRUE`/ausente → produto cartesiano |
| Comma join implícito | `FROM a, b` — heurística textual (AST normaliza p/ CROSS) |
| Predicado não-sargável | função sobre coluna em `WHERE` (`CAST`, `UPPER`, `DATE_TRUNC`…) |
| `ORDER BY` global | sort cara sem `LIMIT` |
| `UNION` sem `ALL` | dedup implícito cara |
| `COUNT(DISTINCT)` | agregação cara; em Trino sugere-se `approx_distinct` |
| `IN` list grande | dezenas de literais — avaliar tabela temporária/join |
| Scan sem filtro | tabela lida por inteiro sem predicado |

Metadados estruturados extraídos: tabelas, aliases, CTEs (com distinção
CTE≠tabela), grafo de joins, predicados, subqueries, cláusulas. O grafo
alimenta o `join-intelligence-analyzer` em `spark optimize`.

## Contexto e semântica

O analyzer distingue aparência de intenção: `SELECT *` dentro de
`EXISTS`/`COUNT` é idiomático e não gera achado. Mas **AST não prova
equivalência semântica** — antes de reescrever uma query, passe pela
checklist: schema de saída, tipos, semântica de NULL, duplicatas,
cardinalidade, ordenação, regras de negócio. O analyzer nunca reescreve
SQL por você.

## Estatísticas opcionais

Com descritor de stats (`--stats` em `spark optimize`), predicados sobre
colunas de alta cardinalidade podem ganhar aviso de seletividade — sempre
declarado como estimativa, nunca como fato.

## Interpretação

- `CONFIRMED`: propriedade sintática certa (comma join, cartesiano).
- `POSSIBLE`: provavelmente custoso (ORDER BY sem LIMIT pode ser
  intencional em agregações pequenas).
- Achados trazem o fragmento SQL como evidência (sanitizado).

## Problemas comuns

| Sintoma | Ação |
|---|---|
| `SQL não parseado como dialeto X` | troque `--dialect`; se nem trino nem spark parseiam, a query usa sintaxe não-SQLGlot — relatório declara a limitação |
| achado que é intencional | `POSSIBLE` não é acusação — a validação sugerida diz como confirmar |
| CTE tratada como tabela | não acontece — CTEs são registradas separadamente nos metadados |
