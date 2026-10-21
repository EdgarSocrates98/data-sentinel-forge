---
name: data-sentinel-report
description: "Use quando for preciso renderizar um relatório de diagnóstico já persistido (`data-sentinel report show`), re-renderizar um JSON exportado, ou exportar um DiagnosticReport como bundle Doctor (forge-contracts/1) para handoff a outra Forja. Perguntas típicas: 'mostra o relatório daquela investigação', 'exporta esse diagnóstico', 'gera o markdown do report'."
metadata:
  contract: data-sentinel/skill/v1
  primary_verbs:
  - data-sentinel report show
  - data-sentinel report export
---

# Data Sentinel — Relatórios

Renderização e exportação de `DiagnosticReport`.

## Quando usar

- Re-renderizar relatório persistido ou exportado — terminal, markdown,
  JSON (`--format`).
- Exportar para o ecossistema Forge: `report export` emite o bundle
  `forge-contracts/1` que o Forge Doctor importa.

## Procedimento

1. `data-sentinel report show --input <report_id|arquivo.json>
   --format markdown` — `--input` aceita id persistido ou path.
2. `data-sentinel report export --input <id>` para o bundle Doctor.
3. Novas análises já persistem o relatório por padrão; `--no-persist`
   desliga.

## Limitações

- Exportação é read-only sobre o relatório: nenhum dado do workload é
  re-analisado ou mutado.
- Relatórios nunca contêm segredos; se aparecer um, é bug — reporte.
