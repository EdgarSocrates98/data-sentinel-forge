# Sentinel Control Center

Portal web (Angular 19) + API HTTP (FastAPI) para operar investigações,
explorar evidências e inspecionar capacidades — tudo sobre o núcleo
determinístico existente. Nenhum dado é simulado: telas vazias são vazias,
erros são reais, e toda análise delega aos analyzers/tools do core.

## Pré-requisitos

| Componente | Versão verificada |
|---|---|
| Python | ≥ 3.11 (3.12 usado no ciclo) |
| Node.js | v22.23.2 |
| Angular | 19.2.x (instalado 19.2.25) |
| Extras Python | `api` → `fastapi` + `uvicorn` |

## Como rodar

```bash
# 1. API (deste repositório)
uv sync                      # instala deps incl. fastapi/uvicorn (grupo dev)
uv run data-sentinel serve --port 8790
#   bind padrão 127.0.0.1; --root <dir> restringe raízes de arquivo (repetível)
#   bind não-local imprime aviso — a API expõe arquivos locais

# 2. Frontend — desenvolvimento
cd frontend
npm ci
npx ng serve --port 4200     # http://localhost:4200 (build dev)

# 2'. Frontend — build de produção servido estaticamente
cd frontend
npx ng build --configuration production
npx serve -s dist/frontend/browser -l 4200   # ou qualquer static server
```

O portal consome `environment.apiBaseUrl` = `http://127.0.0.1:8790/api/v1`
(configurável em `frontend/src/environments/`). CORS da API já permite
`localhost:4200` / `127.0.0.1:4200`.

## Endpoints (todos sob `/api/v1`)

| Método | Caminho | Função |
|---|---|---|
| GET | `/health` | status + versão do pacote + versão da API |
| GET | `/capabilities` | descriptors de capacidades dos analyzers |
| GET | `/tools` | manifesto de tools do registry |
| GET | `/agents` | descriptors dos especialistas |
| GET | `/severities` | enum de severidades |
| POST | `/investigations` | cria investigação (`{problem, files:{tool:path}}`) → 201 |
| GET | `/investigations` | lista investigações **desta sessão** |
| GET | `/investigations/{id}` | relatório completo (redigido) |
| GET | `/investigations/{id}/stream` | SSE de eventos da investigação |
| GET | `/investigations/{id}/graph` | grafo de evidência (incident graph) |
| POST | `/analyze/{analyzer_id}` | delega 1 analyzer sobre `{file: path}` |

OpenAPI interativo: `GET /api/docs` (Swagger UI), schema em
`/api/openapi.json`.

### Caminhos de arquivo

`files`/`file` aceitam **paths absolutos** resolvidos contra raízes
permitidas: `--root` (repetível) ou, por padrão, o diretório de trabalho do
processo e `~/.cache`. Fora das raízes → `403`; extensão fora da allowlist
(`.json .log .txt .sql .yaml .yml .plan .xml .csv .jsonl`) → `400`;
inexistente → `404`.

## Modelo de segurança

- **Bind local por padrão** (`127.0.0.1`); `--host` não-local emite aviso.
- **Sem credenciais no browser**: nenhuma chave AWS/token é exposta; payloads
  passam por redação best-effort de chaves secretas (`password`, `token`,
  `secret`, `access_key`, …). Efeito colateral conhecido: o contador
  `tokens_used` do relatório aparece como `***` (over-redaction cosmética).
- **Rate limit**: 120 req/min por cliente (token bucket in-memory).
- **Payload limit**: 10 MB por request.
- **Audit log**: trilha in-memory append-only (≤10k entradas) de
  cliente/rota/status.
- **Sem auth multi-usuário**: escopo é ferramenta local de engenharia —
  **não** exponha a porta fora de `localhost`.

## Limitações (declaradas)

- **Estado em memória**: investigações e streams vivem no processo; restart
  apaga o histórico. Persistência é backlog (Cycle 07).
- **Sem histórico entre sessões**: `GET /investigations` lista só a sessão
  corrente; relatórios persistidos ficam na CLI (`data-sentinel report show`).
- **Sem multi-hop entre especialistas** e sem chamadas AWS de produção no
  portal (read-only assume o mesmo perfil `offline` da CLI).
- **Contraste/UX**: ver achados corrigidos e backlog em
  [../cycles/cycle-06-visual-homologation.md](../cycles/cycle-06-visual-homologation.md).

## Estrutura do frontend

```text
frontend/src/app/
├── core/            # ApiService (HttpClient tipado), i18n (pt-BR default +
│                    # en), theme (dark default), interceptor de erro, models
├── shared/          # page-shell, analysis-result, helpers de status
├── features/        # dashboard, investigations (list/new/detail + SSE),
│                    # evidence-graph, workloads (Glue/EMR), spark-plans,
│                    # quality-lineage, agents, reports
└── styles/          # tokens.css — 3 camadas (primitive/semantic/component)
```

Rotas lazy: `/`, `/investigations`, `/investigations/new`,
`/investigations/:id`, `/evidence-graph`, `/workloads`, `/spark-plans`,
`/quality-lineage`, `/agents`, `/reports`.

Testes do portal:

```bash
cd frontend
npx ng test --watch=false --browsers=ChromeHeadless   # 49 specs
```
