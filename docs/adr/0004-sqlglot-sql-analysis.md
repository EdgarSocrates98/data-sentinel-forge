# ADR 0004 — SQLGlot para análise estática de SQL

**Status:** accepted
**Data:** Cycle 01 (ds-0006)

## Contexto

O Cycle 01 precisa de análise estática de SQL sem executar queries, cobrindo
diferenças reais entre dialetos Spark e Trino/Athena.

## Decisão

Usar **SQLGlot** como parser: gera AST por dialeto (`spark`, `trino`), é
mantido ativamente e já usado em ferramentas de data eng amplamente adotadas.
O analyzer declara explicitamente que não observa execução física e nunca
executa `EXPLAIN` ou consulta catálogos.

## Consequências

- Detecções AST-driven (joins, CTEs, UNION, funções em predicados) em vez de
  regex frágeis sobre texto.
- Limitação aceita: algumas normalizações do parser apagam sintaxe original
  (ex.: comma join vira CROSS), então um check complementar em texto é usado —
  documentado no código.
- Quando o parse falha, o resultado é um achado UNKNOWN + limitação — nunca
  crash nem diagnóstico inventado.
