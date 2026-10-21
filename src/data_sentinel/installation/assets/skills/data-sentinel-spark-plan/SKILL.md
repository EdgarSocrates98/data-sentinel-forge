---
name: data-sentinel-spark-plan
description: "Use quando tiver a saída de df.explain()/EXPLAIN salva em arquivo, ou um log de execução Spark/Glue, e precisar de achados ancorados em evidência — `data-sentinel spark explain --file` analisa o plano físico (scans, shuffles, joins, agregações) e `data-sentinel analyze --file` cobre o log (OOM, skew, falhas de executor/driver). Use também para a análise composta SQL + joins/cardinalidade + config com `data-sentinel spark optimize --sql --config --stats`. Perguntas típicas: 'por que esse job faz tanto shuffle', 'onde está o gargalo', 'o plano lê a tabela inteira?'."
---

# Data Sentinel — Plano físico Spark

`data-sentinel spark explain --file` lê o `explain()` salvo e emite
findings com evidência. O que ele **não** faz é inventar o que o texto
não diz: `explain()` é saída para humano, e o que o parser não ancora em
evidência sai como limitação, não como achado.

## Quando usar

- Você tem um `explain` (qualquer modo) num arquivo e quer saber o que o
  plano declara: scans, `Exchange`/shuffle, estratégia de join, Sort,
  Window, `HashAggregate`.
- Você tem o log do run (driver/executor) e quer os achados de OOM,
  skew, perda de executor e padrões de falha: `analyze --file`.
- Você quer a análise composta: SQL estático + cardinalidade de joins +
  advisor de configs: `spark optimize --sql`.

## Procedimento

1. **Salve o plano.** `df.explain("formatted")` é o formato preferido;
   `df.explain(True)` mostra os planos lógicos e o físico; `df.explain("cost")`
   traz estatísticas estimadas. Redirecione a saída para um `.txt`.
2. **Analise o plano.**

   ```bash
   data-sentinel spark explain --file plano.txt --format markdown --output plano.md
   ```

   Saída: findings (`category`, `severity`, `status`, `evidence_ids`),
   `limitations` e `summary`. `--json` para automação, `--quiet` para só
   o resumo.
3. **Se há log do run, junte as duas leituras.** `data-sentinel analyze
   --file job.log --platform spark` extrai os achados de execução (OOM,
   skew, retries, executor perdido) que o plano declarante não mostra.
4. **Para a leitura composta**: `data-sentinel spark optimize --sql
   query.sql --config spark-defaults.conf --stats stats.json` corre SQL
   estático + joins/cardinalidade + config no mesmo relatório.

## Red flags

- **Plano declarado ≠ plano executado.** O `explain` não revela
  distribuição real, spill, GC nem a estratégia que o AQE escolheu em
  runtime. Afirmar causa só pelo plano, sem métrica de execução, é a
  fraude clássica — para causa, junte o log (passo 3).
- **Não leia "sem finding" como "job saudável".** Se a entrada estava
  truncada ou num formato fora do suportado, a saída diz `limitations` —
  regenere o `explain` antes de concluir.
- Config derivada sem medida é chute: propostas de tuning precisam do
  artefato que as sustente, nunca de valor de memória.

## Saída e despacho

Findings com `status` ∈ `CONFIRMED | PROBABLE | POSSIBLE | UNKNOWN` e
`evidence_ids` apontando para os trechos sanitizados do arquivo.

Esta skill é **despachável** (`subagent: true` no espelho
`.agents/skills/`): investigação fechada sobre artefato já em disco. Se
rodar como subagente, não peça confirmação a ninguém — o que precisar de
decisão volta como limitação do relatório.
