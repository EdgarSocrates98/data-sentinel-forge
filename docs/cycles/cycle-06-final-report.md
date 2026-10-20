# Cycle 06 — Relatório final

**Decisão: `APPROVED WITH RESTRICTIONS`**
**SHA da main:** `e84c7909461acc040cdf38e80f18095016857b37` (pré-ds-0079;
mudanças deste spec pendentes de commit pelo orquestrador)

## Specs executados

| Spec | Título | Escopo |
|---|---|---|
| ds-0070 | Foundation hardening gate | baseline auditada antes do portal |
| ds-0071 | Backend Control Center API | FastAPI real `/api/v1/*` |
| ds-0072 | Angular foundation + design system | scaffold, tokens 3-layer, i18n |
| ds-0073 | Investigation Studio | lista/nova/detalhe + SSE |
| ds-0074 | Evidence Graph Explorer | grafo SVG real derivado do relatório |
| ds-0075 | Workload Explorer Glue/EMR + Spark plans | rotas reais mínimas |
| ds-0076 | Quality & Lineage Studio + Agent Ops | rotas reais mínimas |
| ds-0077 | Reporting & History | sessão corrente, export |
| ds-0078 | Security/perf/reliability + testes | rate limit, payload, path guard |
| ds-0079 | Homologação visual + build/dist + docs + relatório | este documento |

## O que entrou

API FastAPI real (`src/data_sentinel/api/app.py`, `data-sentinel serve`)
delegando ao núcleo — registry/tools/investigator/incident-graph, zero
lógica de diagnóstico duplicada. Portal Angular 19 standalone (signals,
OnPush, lazy routes) com design system próprio (tokens CSS 3-layer,
dark default + light, pt-BR default + en, WCAG AA auditada). Studios:
Dashboard, Investigations (list/new/detail + SSE), Evidence Graph,
Workloads (Glue/EMR), Spark Plans, Quality & Lineage, Agents, Reports —
todas rotas reais; vazios e erros são honestos.

## Verificação (números reais desta máquina)

- **Backend**: `uv run pytest -q` → **745 passed, 4 skipped**
  (env-gated AWS real); `ruff check src tests` limpo;
  `mypy src` strict limpo.
- **Frontend**: `npx ng test` → **49/49 SUCCESS** (Chrome Headless);
  `npx ng build --configuration production` → **initial 349.39 kB raw /
  ~95.81 kB transfer**, lazy chunks por studio (1–29 kB).
- **Packaging**: `python -m build` → `data_sentinel-0.1.0.tar.gz` +
  `-py3-none-any.whl` limpos; wheel instalada em venv fresco e
  `data-sentinel serve` responde `/api/v1/health` (`{"status":"ok",
  "version":"0.1.0","api":"v1"}`), 10 paths no OpenAPI.
- **API real**: `POST /investigations` → 201; SSE stream com eventos
  reais; `POST /analyze/sql.analyze` delega ao analyzer real.
- **Homologação visual**: 32 screenshots em
  `docs/assets/cycle06/` — todas as rotas × dark/light + mobile 390px +
  estado de erro; evidência completa em
  `docs/cycles/cycle-06-visual-homologation.md`.
- **A11y**: auditoria programática de contraste (alfa composto) em 6
  rotas × 2 temas → **0 violações AA** pós-correção; Tab order =
  skip link → toggles → nav em ordem visual; anel de foco 3px.
- **Responsivo**: overflow horizontal de documento a 390px = **0px** em
  todas as rotas (achados P1 corrigidos neste spec).

## Quality gates (§17)

- **P0 abertos: nenhum.** Sem secrets expostos (redação ativa), API só
  localhost, zero mutação cloud, UI sem dados fictícios, sem XSS
  conhecido introduzido (ver restrição Angular abaixo).
- **P1 corrigidos neste spec**: contraste light-theme (7 tokens),
  overflow de tabelas a 390px.
- **P1 residual**: grafo com poucas arestas quando `report.evidence` vem
  vazio (lacuna declarada, não inventada); `tokens_used` mascarado como
  `***` pela redação (over-redaction cosmética).

## Restrições honestas

- **Estado 100% em memória** — investigações/stream/histórico morrem com
  o processo; sem persistência entre sessões (MVP deliberado).
- **Sem chamadas AWS de produção** — portal opera no mesmo perfil
  offline/read-only da CLI; conectores AWS seguem env-gated.
- **CI remota bloqueada por billing** (repo privado) — equivalência local
  comprovada com os mesmos comandos.
- **npm audit**: 40 advisories (2 critical: `piscina`, `tar` — ambos
  build-time, não vão no bundle; 4 high em runtime `@angular/*` 19.2.25 —
  advisories <=19.2.25; mitigação exige bump Angular 20+/21 breaking).
  Sem `audit fix --force` aplicado — dívida registrada.
- **Sem delegação multi-hop** entre especialistas; RAG sem embeddings
  (herdado do Cycle 05).
- **`tokens_used` → `***`**: redação por substring `token` mascara o
  contador de uso — over-redaction cosmética, backlog.
- **Serve SPA separado** (ADR 0013): uso final exige API + static server;
  single-process fica para quando houver consumidor.
- **Portabilidade**: homologado em Linux; Windows/macOS não exercitados
  nesta máquina (scripts são portable-first, sem Docker obrigatório).
- **axe-core não executado**: contraste foi auditado por computed styles;
  scan automatizado completo fica para o Cycle 07.

## Backlog Cycle 07

- Persistência de investigações (SQLite store já existe no núcleo).
- Bump Angular ≥20 + resolução da dívida npm audit (breaking, decidido
  fora de RC).
- Scan axe-core + testes E2E Playwright versionados (hoje o script é
  ad-hoc em `/tmp` — homologar e commitar).
- Popular `report.evidence` nas rotas tool-only para grafos mais ricos.
- Corrigir over-redaction de `tokens_used` (whitelist de contadores).
- Nav mobile hamburger (P2); Firefox/WebKit na homologação; métricas de
  performance de grafo com volumes maiores.
- Avaliar `--with-ui` single-process se surgir consumidor (ADR 0013).

## Documentação atualizada neste spec

- `docs/architecture.md` — seção Control Center + camadas reais (api,
  agents, mcp); removidas notas de placeholder obsoletas.
- `docs/guides/control-center.md` — run, endpoints, segurança, limitações.
- `docs/cli.md` — comando `serve`.
- `README.md` — seção Control Center + estado do projeto atualizado
  (estava em Cycle 02).
- `docs/adr/0013-frontend-distribution.md` — decisão de distribuição (§15).
- `docs/cycles/cycle-06-visual-homologation.md` — homologação §14.
