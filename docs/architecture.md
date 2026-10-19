# Arquitetura

Monólito modular (ver [ADR 0001](adr/0001-modular-monolith.md)) — um pacote
`data_sentinel` com fronteiras internas por domínio. Comunicação entre módulos
somente via contratos públicos.

```text
┌──────────────────────────────────────────────────────┐
│ cli/ (Typer — orquestração fina, PT-BR, exit codes)  │
└──────┬───────────────┬───────────────┬───────────────┘
       ▼               ▼               ▼
  core/config     core/security    persistence/
  load_config     path guard       SQLite store
  precedence      read_input_file  migrations
       │          redact/sanitize       ▲
       ▼               ▲                │
  analyzers/protocol + registry ────────┘
       ├── spark/log_analyzer  (padrões regex curados)
       └── sql/sql_analyzer    (SQLGlot AST, dialetos)
       ▼
  core/contracts — DiagnosticRequest, Evidence, Finding,
  DiagnosticReport (schema_version 1.0.0), …
```

## Fluxo de `analyze`

1. `load_config` resolve perfil/limites/fontes.
2. `safe_resolve` valida o caminho contra `cwd + allowed_roots`.
3. `read_input_file` aplica limite de tamanho e rejeita binário.
4. `DiagnosticRequest` é montado; `registry.for_source_type` seleciona o(s)
   analyzer(s).
5. `analyze()` retorna `AnalysisResult` (findings + evidence + limitations).
6. `_build_report` agrega num `DiagnosticReport` versionado.
7. `SentinelStore.save_analysis` persiste relatório + evidências sanitizadas.
8. Saída: texto PT-BR ou `--json`.

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
- **`persistence`**: SQLite stdlib, migrations numeradas append-only, valores
  sempre parametrizados. Guarda o documento JSON do contrato — não raw files.
- **Placeholders**: `api/`, `mcp/`, `intelligence/`, `connectors/` existem como
  pacotes vazios para os ciclos futuros — nenhuma implementação falsa.

## Princípios

- Determinístico antes de LLM; evidência antes de conclusão.
- Read-only por padrão; offline funcional sem rede.
- Nada de "vazio com cara de cheio": achados fracos ficam `UNKNOWN`.
