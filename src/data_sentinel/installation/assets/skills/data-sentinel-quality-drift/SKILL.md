---
name: data-sentinel-quality-drift
description: "Use quando houver um contrato declarativo de qualidade de dados para validar offline, exports de resultados de checks para normalizar em observações, ou a pergunta for sobre drift/regressão de qualidade — volume, freshness, schema, pass-rate. Cobre `data-sentinel quality validate|import` e as tools MCP `sentinel.quality.assess`/`sentinel.quality.detect_drift`. Perguntas típicas: 'a qualidade desse dataset regrediu?', 'esse contrato de qualidade é válido?'."
---

# Data Sentinel — Qualidade e Drift

Qualidade declarativa e detecção de drift entre observações.

## Quando usar

- Validar um contrato de qualidade antes de ancorá-lo num pipeline.
- Normalizar resultados exportados de engines de check em observações
  Sentinel.
- Perguntas de regressão: volume caiu, freshness estourou, schema mudou.

## Procedimento

1. Valide o contrato (estático, offline):
   `data-sentinel quality validate --file contrato.yaml`.
2. Normalize exports de checks: `data-sentinel quality import --file
   resultados.json` — o Sentinel nunca executa checks contra o dado.
3. Drift via MCP: `sentinel.quality.assess` (uma observação) e
   `sentinel.quality.detect_drift` (baseline_file + current_file).
4. Impacto downstream: ingere eventos OpenLineage com `data-sentinel
   lineage ingest` e consulta alcançabilidade com `data-sentinel lineage
   impact` (ou as tools MCP `sentinel.lineage.ingest`/`impact`).

## Limitações

- Drift sem observações exportadas não é diagnosticável — se não há
  export, a resposta honesta é "sem evidência de qualidade coletada".

Esta skill é **despachável** (`subagent: true` no espelho
`.agents/skills/`): validação e normalização sobre artefatos já em
disco. Se rodar como subagente, não peça confirmação — o que precisar de
decisão volta como limitação do relatório.
