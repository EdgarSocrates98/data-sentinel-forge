# Arquitetura

Monólito modular (ver [ADR 0001](adr/0001-modular-monolith.md)) — um pacote
`data_sentinel` com fronteiras internas por domínio. Comunicação entre módulos
somente via contratos públicos.

```text
┌──────────────────────────────────────────────────────┐
│ cli/ (Typer — orquestração fina, PT-BR, exit codes)  │
│   analyze/report/doctor/… + glue/spark/sql/report    │
└──────┬───────────────┬───────────────┬───────────────┘
       ▼               ▼               ▼
  diagnostics/     core/security    persistence/
  orchestrator     path guard       SQLite store
  correlation      read_input_file  migrations
  timeline         redact/sanitize       ▲
       │               ▲                │
       ▼               │                │
  analyzers/protocol + registry ────────┘
       ├── spark/log_analyzer   (padrões regex curados)
       ├── spark/plans          (EXPLAIN → árvore)
       ├── spark/joins          (cardinalidade + stats declaradas)
       ├── spark/config         (advisor + matriz runtime)
       ├── sql/sql_analyzer     (SQLGlot AST, dialetos)
       └── cloudwatch/analyzer  (logs AWS)
       ▼
  reporting/render — terminal | json | markdown
       ▼
  core/contracts — DiagnosticRequest, Evidence, Finding,
  DiagnosticReport (schema_version 1.0.0), …

  connectors/aws/  (extra [aws]) — glue + cloudwatch_logs,
  allowlist read-only, paginação limitada, recusa offline
```

## Fluxo de `analyze`

1. `load_config` resolve perfil/limites/fontes.
2. `safe_resolve` valida o caminho contra `cwd + allowed_roots`.
3. `read_input_file` aplica limite de tamanho e rejeita binário.
4. `DiagnosticRequest` é montado; o **orquestrador** seleciona analyzers por
   `SourceType`, executa em ordem determinística, cronometra `duration_ms`
   e converte falha de analyzer em limitação do relatório.
5. `analyze()` retorna `AnalysisResult` (findings + evidence + limitations).
6. `DiagnosticReport` versionado agrega resultados + recomendações.
7. `SentinelStore.save_analysis` persiste relatório + evidências sanitizadas.
8. Saída via `reporting/`: terminal PT-BR, `--json` ou `--format markdown`.

## Camadas

- **`core/contracts`**: única fonte de verdade das entidades públicas
  (Pydantic v2). `schema_version` em todo relatório; JSON Schemas exportados
  para `schemas/`.
- **`core/exceptions`**: `SentinelError(code, message, details)` — nenhum
  `raise Exception` nu; mensagens de usuário em PT-BR.
- **`core/security`**: primitivas sem dependência externa — path guard,
  leitura com limites, sanitização (ANSI/controle), redação de segredos.
- **`analyzers`**: protocolo ABC (`analyzer_id`, `version`, `validate_input`,
  `analyze`, `capabilities`) + registry com rejeição de duplicados. Cada
  analyzer declara um `CapabilityManifest` com suas limitações.
- **`diagnostics`**: `orchestrator` (execução determinística, degradação de
  falhas, agregação de recomendações), `correlation` (falhas relacionadas),
  `timeline` (só timestamps observados).
- **`reporting`**: renderers terminal/JSON/Markdown sobre `DiagnosticReport`
  — apresentação fora dos analyzers (ADR 0010).
- **`connectors/aws`**: Glue + CloudWatch read-only via allowlist de ações;
  `boto3` é extra `[aws]`; perfil `offline` recusa instanciar.
- **`agents` + `tools` + `context`** (Cycle 05): runtime agêntico com budgets,
  registry de tools, especialistas com responsabilidades delimitadas,
  providers determinísticos (stub) ou HTTP local.
- **`mcp`/`mcp_server`** (Cycle 05): servidor MCP stdio via SDK oficial.
- **`api`** (Cycle 06): ver seção Control Center abaixo.
- **`persistence`**: SQLite stdlib, migrations numeradas append-only, valores
  sempre parametrizados. Guarda o documento JSON do contrato — não raw files.
- **Placeholders**: `intelligence/` permanece para ciclos futuros —
  nenhuma implementação falsa.

## Control Center (Cycle 06)

API HTTP + portal Angular sobre o núcleo existente — nenhuma lógica de
diagnóstico foi duplicada na camada web.

```text
┌─────────────────────────────────────────────────────────────┐
│ frontend/ (Angular 19, standalone + signals + OnPush)       │
│   design system próprio — tokens CSS 3-layer, pt-BR/en,     │
│   tema dark/light; lazy routes por studio                   │
└──────────────┬──────────────────────────────────────────────┘
               │ HTTP/SSE — http://127.0.0.1:8790/api/v1
               ▼
┌─────────────────────────────────────────────────────────────┐
│ api/app.py — FastAPI factory (`data-sentinel serve`)        │
│   CORS localhost-only · rate limit 120/min · payload ≤10MB  │
│   path guard (allowed roots) · redação de segredos · audit  │
└──┬───────────┬───────────────┬───────────────┬──────────────┘
   ▼           ▼               ▼               ▼
 tools/    agents/         diagnostics/    analyzers/
 registry  investigator    incident graph  analyzers reais
```

Regras de fronteira mantidas:

- Endpoints delegam ao núcleo (`build_default_registry`, `execute_tool`,
  `investigate`, `build_incident_graph`, descriptors de capacidades) —
  **zero reimplementação** de analyzer/diagnóstico no handler.
- Versão de API em `/api/v1/*`; OpenAPI exposto em `/api/openapi.json`.
- Estado de investigações **em memória** por processo (deliberado no MVP;
  persistência é backlog do Cycle 07).
- Bind padrão `127.0.0.1`; bind não-local imprime aviso explícito.
- O frontend é estaticamente buildado (`frontend/dist/`) e servido por
  qualquer servidor estático ou `ng serve`; a API é consumida via
  `environment.apiBaseUrl`. Ver [docs/guides/control-center.md](guides/control-center.md).

## Princípios

- Determinístico antes de LLM; evidência antes de conclusão.
- Read-only por padrão; offline funcional sem rede.
- Nada de "vazio com cara de cheio": achados fracos ficam `UNKNOWN`.
