---
name: data-sentinel-report
description: "Use quando for preciso renderizar um relatório de diagnóstico já persistido (`data-sentinel report show`), re-renderizar um JSON exportado, ou exportar um DiagnosticReport como bundle Doctor (forge-contracts/1) para handoff a outra Forja. Perguntas típicas: 'mostra o relatório daquela investigação', 'exporta esse diagnóstico', 'gera o markdown do report'."
---

# Data Sentinel — Relatórios

Renderização e exportação de `DiagnosticReport`.

## Quando usar

- Re-renderizar relatório persistido ou exportado — terminal, markdown,
  JSON (`--format`).
- Exportar para o ecossistema Forge: `report export` emite o bundle
  `forge-contracts/1` que o Forge Doctor importa.

## Procedimento

1. `data-sentinel report show --id <report_id> --format markdown` —
   `--file <arquivo.json>` para um relatório exportado em disco.
2. `data-sentinel report export --file <report.json> [--output bundle.json]`
   para o bundle Doctor.
3. Novas análises já persistem o relatório por padrão; `--no-persist`
   desliga.

## Limitações

- Exportação é read-only sobre o relatório: nenhum dado do workload é
  re-analisado ou mutado.
- Relatórios nunca contêm segredos; se aparecer um, é bug — reporte.

Esta skill é **despachável** (`subagent: true` no espelho
`.agents/skills/`): renderiza relatório persistido/exportado sem decidir
nada. Se rodar como subagente, não peça confirmação — o que precisar de
decisão volta como limitação do relatório.
