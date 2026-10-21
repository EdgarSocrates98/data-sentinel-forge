---
name: data-sentinel-quality-drift
description: "Use quando houver um contrato declarativo de qualidade de dados para validar offline, exports de resultados de checks para normalizar em observações, ou a pergunta for sobre drift/regressão de qualidade — volume, freshness, schema, pass-rate. Cobre `data-sentinel quality validate|import` e as tools MCP `sentinel.quality.assess`/`sentinel.quality.detect_drift`. Perguntas típicas: 'a qualidade desse dataset regrediu?', 'esse contrato de qualidade é válido?'."
metadata:
  contract: data-sentinel/skill/v1
  primary_verbs:
  - data-sentinel quality validate
  - data-sentinel quality import
  - data-sentinel lineage
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
4. Impacto downstream: `data-sentinel lineage ...` /
   `sentinel.lineage.ingest`+`impact`.

## Limitações

- Drift sem observações exportadas não é diagnosticável — se não há
  export, a resposta honesta é "sem evidência de qualidade coletada".
