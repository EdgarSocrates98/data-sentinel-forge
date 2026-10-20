# Cycle 06 — Homologação visual (ds-0079, §14)

Homologação executada contra o **build de produção real** — nada simulado:

- **Backend**: `uv run data-sentinel serve --port 8790` (FastAPI/uvicorn,
  bind 127.0.0.1). Health: `GET /api/v1/health → {"status":"ok","version":"0.1.0","api":"v1"}`.
- **Frontend**: `npx ng build --configuration production` → `frontend/dist/frontend/browser`
  servido estaticamente em `http://127.0.0.1:4200` (`serve -s`, fallback SPA).
- **Browser**: Chromium 156 headless via Playwright 1.64.1 (Node v22.23.2).
- **Data da execução**: Cycle 06, branch de trabalho ds-0079.

## Fluxo real exercitado

Investigação criada pela API real antes das capturas:

```text
POST /api/v1/investigations → 201  inv-d54a98e66dbc
  problem: "Spark OOM investigation"
  files:   {"sentinel.sql.analyze": "fixtures/sql/cycle2/cast_keys.sql"}
GET /api/v1/investigations/inv-d54a98e66dbc
  agents_used: ["spark-expert"]   tools_used: ["sentinel.sql.analyze"]
  findings: 4 (MEDIUM/POSSIBLE, HIGH/POSSIBLE, LOW/UNKNOWN, INFO/UNKNOWN)
  limitations: análise estática declarada (sem plano físico, sem cardinalidade real)
GET .../stream → SSE real: INVESTIGATION_STARTED, TOOL_COMPLETED,
  INVESTIGATION_COMPLETED {"findings":4}
GET .../graph  → 4 nós, 0 arestas (ver limitações abaixo)
POST /api/v1/analyze/sql.analyze → relatório real do analyzer (delegação direta)
```

A página de detalhe fotografada em `homologation-investigation-detail-*.png`
mostra os 4 findings reais, badges de severidade/confiança, limitações e
metadados — sem dado fictício.

## Matriz de captura (1440×900, ambos os temas)

| Rota | Dark | Light | HTTP | Console |
|---|---|---|---|---|
| `/` (Visão geral) | [shot](../assets/cycle06/homologation-dashboard-dark.png) | [shot](../assets/cycle06/homologation-dashboard-light.png) | 200 | limpo |
| `/investigations` | [shot](../assets/cycle06/homologation-investigations-dark.png) | [shot](../assets/cycle06/homologation-investigations-light.png) | 200 | limpo |
| `/investigations/new` | [shot](../assets/cycle06/homologation-investigations-new-dark.png) | [shot](../assets/cycle06/homologation-investigations-new-light.png) | 200 | limpo |
| `/investigations/<id>` (dados reais) | [shot](../assets/cycle06/homologation-investigation-detail-dark.png) | [shot](../assets/cycle06/homologation-investigation-detail-light.png) | 200 | limpo |
| `/evidence-graph` (picker) | [shot](../assets/cycle06/homologation-evidence-graph-dark.png) | [shot](../assets/cycle06/homologation-evidence-graph-light.png) | 200 | limpo |
| `/evidence-graph?investigation=<id>` | [shot](../assets/cycle06/homologation-evidence-graph-selected-dark.png) | [shot](../assets/cycle06/homologation-evidence-graph-selected-light.png) | 200 | limpo |
| `/workloads` | [shot](../assets/cycle06/homologation-workloads-dark.png) | [shot](../assets/cycle06/homologation-workloads-light.png) | 200 | limpo |
| `/spark-plans` | [shot](../assets/cycle06/homologation-spark-plans-dark.png) | [shot](../assets/cycle06/homologation-spark-plans-light.png) | 200 | limpo |
| `/quality-lineage` | [shot](../assets/cycle06/homologation-quality-lineage-dark.png) | [shot](../assets/cycle06/homologation-quality-lineage-light.png) | 200 | limpo |
| `/agents` | [shot](../assets/cycle06/homologation-agents-dark.png) | [shot](../assets/cycle06/homologation-agents-light.png) | 200 | limpo |
| `/reports` | [shot](../assets/cycle06/homologation-reports-dark.png) | [shot](../assets/cycle06/homologation-reports-light.png) | 200 | limpo |
| Estado de erro (`/investigations/inv-inexistente`) | [shot](../assets/cycle06/homologation-error-state-dark.png) | — | 200 (API 404) | 404 esperado |

## Achados e correções aplicadas neste spec

| # | Achado | Severidade | Correção |
|---|---|---|---|
| 1 | Tema claro abaixo de WCAG AA em botões primários e skip link (branco sobre `#0284c7` = 4.1:1) | P1 | `--ds-accent-emphasis` → `--ds-p-cyan-700`; hover escuro `--ds-p-cyan-800` |
| 2 | Tema claro: chips `ok`/success 3.02:1, `MEDIUM`/warning 4.02–4.31:1, `UNKNOWN` 3.77:1 | P1 | Novos primitivos `emerald-800`/`amber-800`/`orange-800`; `confidence-unknown` → `slate-600`; `-bg` equivalents realinhados |
| 3 | Overflow horizontal do documento a 390px: `/investigations` +50px, detalhe +396px | P1 | A classe `.table-scroll` era referenciada nos templates mas **nunca definida** no CSS (divs inertes) — classe criada em `styles.css`, wrappers adicionados onde faltavam (evidence-graph, detail, lista); `.sr-only` com `left:0` (abspos fora de scroller estendia o canvas) |
| 4 | Pós-correção: auditoria programática de contraste (composição alfa real) = **0 falhas AA** nas rotas auditadas, ambos os temas; overflow de documento a 390px = **0px** em todas as rotas | — | re-verificado com Playwright |

## Auditorias executadas

- **Contraste (WCAG 2.2 AA)**: amostragem de computed styles de todos os
  elementos textuais visíveis em 6 rotas × 2 temas, com composição alfa real
  dos backgrounds (bg translúcido sobre superfície). Resultado pós-correção:
  **0 violações**; dark já estava 0.
- **Navegação por teclado**: ordem de Tab = skip link → toggle de idioma →
  toggle de tema → 8 itens de nav em ordem visual. Anel de foco
  `outline: 3px solid` presente em todos os stops
  ([shot](../assets/cycle06/homologation-keyboard-focus-dark.png)).
- **Responsivo 390px**: sidenav vira strip horizontal com scroll próprio;
  nenhum overflow de documento após correção
  ([shots mobile](../assets/cycle06/homologation-mobile-dashboard-dark.png) e
  `homologation-mobile-*-{dark,light}.png`).
- **Estado vazio**: listas vazias renderizam CTA real ("Nova investigação") —
  sem conteúdo inventado.
- **Estado de erro**: `GET` 404 → página de erro PT-BR com ação "Tentar
  novamente" e explicação honesta sobre estado em memória. O console 404 é o
  fetch real — esperado.
- **Hierarquia/densidade**: leitura dos screenshots — espaçamento consistente
  via tokens `--ds-space-*`, cabeçalhos de página uniformes, cards `ds-card`
  alinhados; nenhum elemento renderiza dado fictício.

## Limitações honestas desta homologação

- **`tokens_used` exibido como `***`**: o middleware de redação mascara
  qualquer chave contendo "token" — inclui o contador de uso do relatório
  (over-redaction cosmética, não é vazamento). Registrado para ajuste.
- **Grafo com poucas arestas**: a investigação SQL-only produz findings sem
  `report.evidence` top-level populado → grafo com nós e poucas/nenhuma
  aresta. O modelo deriva só de referências reais — lacuna declarada, não
  preenchida com arestas inventadas.
- **Nav mobile**: strip horizontal com scroll (decisão consciente); um padrão
  hamburger ficou como backlog P2.
- **Sem axe-core**: a auditoria de contraste foi programática (computed
  styles); um scan axe completo fica como backlog do Cycle 07.
- **Capturas em Chromium apenas**: Firefox/WebKit não homologados nesta
  passada.
- **Estado em memória**: as investigações criadas na homologação
  (`inv-05f23e0e7ae0`, `inv-d54a98e66dbc`) somem ao reiniciar o backend —
  comportamento documentado.
