# Cycle 02 — Arquitetura

Como o ciclo transformou a fundação offline do Cycle 01 em plataforma de
diagnóstico Glue/Spark/SQL — sem quebrar os contratos nem os princípios
determinísticos.

## Visão em camadas (o que mudou)

```text
┌────────────────────────────────────────────────────────────┐
│ CLI (Typer)                                                │
│   analyze │ report │ doctor │ capabilities │ config │ ...  │
│   NOVOS:  glue {inspect,runs,diagnose}                     │
│           spark {explain,optimize}  sql {analyze}          │
│           report {show}                                    │
├────────────────────────────────────────────────────────────┤
│ diagnostics/orchestrator.py        NOVO                    │
│   executa analyzers determinísticos, cronometra,           │
│   degrada falhas em limitações, agrega recomendações        │
├────────────────────────────────────────────────────────────┤
│ reporting/render.py                NOVO                    │
│   terminal │ json │ markdown (separado da análise)         │
├────────────────────────────────────────────────────────────┤
│ analyzers/ (registry auto-registra 6 analyzers)            │
│   SparkGlueLogAnalyzer        (Cycle 01, intacto)          │
│   SqlStaticAnalyzer v0.2.0    (evoluído — AST SQLGlot)     │
│   CloudWatchLogAnalyzer       NOVO                         │
│   SparkPlanAnalyzer           NOVO                         │
│   JoinIntelligenceAnalyzer    NOVO                         │
│   SparkConfigAdvisor          NOVO                         │
├────────────────────────────────────────────────────────────┤
│ diagnostics/                         NOVO                  │
│   correlation.py — agrupa falhas relacionadas              │
│   timeline.py    — sequência por timestamps OBSERVADOS     │
├────────────────────────────────────────────────────────────┤
│ connectors/aws/                      NOVO (extra [aws])    │
│   sessions.py — boto3 opcional, recusa offline             │
│   glue.py     — allowlist GetJob*/GetJobRun* + paginação   │
│   cloudwatch_logs.py — allowlist logs:* + janela/limite    │
├────────────────────────────────────────────────────────────┤
│ api/contracts.py                     NOVO                  │
│   readiness contracts p/ futura API/MCP — SEM servidor     │
├────────────────────────────────────────────────────────────┤
│ core/ (intacto) — contracts, configuration, security       │
│ persistence/ (intacto) — SQLite + migrations               │
└────────────────────────────────────────────────────────────┘
```

## Decisões arquiteturais do ciclo

- **Determinístico-first mantido**: nenhum LLM entrou no caminho de
  execução. Regras curadas + estatísticas declaradas; fraqueza de
  evidência ⇒ `POSSIBLE`/`UNKNOWN`, nunca invenção.
- **AWS por allowlist + extra opcional**: `boto3` é `[aws]` extra;
  `ALLOWED_ACTIONS` limita a operações read-only; perfil `offline` recusa
  instanciar conectores. A cadeia de credenciais é a padrão do SDK —
  o código não toca em segredos.
- **Evidência com proveniência**: `DECLARED` (stats do descritor),
  `STATIC_INFERRED` (AST/plano), `OBSERVED` (runtime metrics). Skew
  suspeito ≠ observado; estimativa do otimizador ≠ medida.
- **Orquestração isolada**: analyzers não se importam entre si —
  contexto flui via `ExecutionContext.extra`/metadados do request
  (ex.: `workload_oom_evidence` para o config advisor).
- **Render separado de análise**: `reporting/` consome
  `DiagnosticReport`/`AnalysisResult` e emite terminal/JSON/Markdown —
  analyzers nunca produzem apresentação.
- **API/MCP = contratos apenas**: `api/contracts.py` define os shapes de
  request/response e um teste de readiness garante coerência com os
  contratos públicos. Sem servidor — adiado por decisão do Grill Gate.
- **Evolução aditiva de contrato**: `SourceType` ganhou `SPARK_PLAN`,
  `GLUE_JOB`, `CLOUDWATCH_LOG`; `AnalysisResult.duration_ms`; schema
  segue `1.0.0` (minor aditivo — ADR 0002).

## Fluxo de um diagnóstico Glue (ds-0017)

`glue diagnose` → `GlueConnector.get_job_run` (allowlist, paginado,
cancelável) → `CloudWatchLogsConnector` (janela+limite) → parser de
eventos → `correlation` + `timeline` → analyzers registrados →
`DiagnosticReport` → renderer → saída/persistência.

Cada etapa falha de forma contida: sem credenciais → `aws.sem_credenciais`
(exit 1); analyzer que lança exceção → limitação no relatório, não crash.

## Pontos de extensão preservados

- `Analyzer` ABC + `registry.register` — 6 analyzers hoje, novos entram
  por registro sem tocar no orquestrador.
- `SourceType`/`Platform` enumeráveis — fixtures e conectores futuros
  (Trino real, Iceberg, Databricks) plugam no mesmo caminho.
- `api/contracts.py` pronto para Cycle 03+ (FastAPI/MCP) sem mudar
  contratos públicos.
