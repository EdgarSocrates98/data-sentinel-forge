---
name: data-sentinel-sql-review
description: "Use quando houver um arquivo .sql ou uma query colada e a pergunta for de review estático — antipadrões, joins sem cardinalidade declarada, SELECT *, funções não-determinísticas, dialeto. `data-sentinel analyze --sql/--file` e `data-sentinel sql ...` cobrem a leitura; a tool MCP é `sentinel.sql.analyze`. Perguntas típicas: 'esse SQL tá certo?', 'por que essa query tá lenta?', 'tem antipadrão aqui?'."
---

# Data Sentinel — SQL Review

Análise estática de SQL: offline, determinística, sem executar a query.

## Quando usar

- Review de query ou script `.sql` antes de merge/deploy.
- "Por que essa query tá lenta" quando só existe o texto do SQL —
  execução real fica fora do escopo (isso é `data-sentinel-spark-plan`
  com o event log).

## Procedimento

1. Arquivo: `data-sentinel sql analyze --file query.sql` — o verbo
   dedicado. `data-sentinel analyze --sql query.sql` é a forma legada
   (`--sql` recebe **caminho de arquivo**, não query inline).
2. Dialeto não-padrão: `--dialect trino` (ou o dialeto alvo) — um
   antipadrão num dialeto pode ser válido noutro.
3. Query colada no chat: salve num `.sql` primeiro — a análise é sobre
   artefato, com a evidência apontando para a linha do arquivo.
4. MCP: a tool `sentinel.sql.analyze` cobre a mesma leitura.
5. Reporte cada achado com a evidência ancorada (cláusula/linha).

## Limitações

- Sem execução: cardinalidade real e tempo são hipóteses qualificadas,
  nunca medições — diga isso ao recomendar reescrita.

Esta skill é **despachável** (`subagent: true` no espelho
`.agents/skills/`): análise estática sobre um `.sql` já em disco. Se
rodar como subagente, não peça confirmação — o que precisar de decisão
volta como limitação do relatório.
