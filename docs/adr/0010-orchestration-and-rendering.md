# ADR 0010 — Orquestração determinística e separação análise/render

- Status: aceito
- Data: Cycle 02 (ds-0017)

## Contexto

Cycle 02 introduziu 4 analyzers novos e múltiplas fontes por diagnóstico
(SQL + stats + config no mesmo `spark optimize`). Precisávamos decidir
como analyzers compõem, como falhas se propagam e quem produz saída.

## Decisão

1. **Orquestrador único** (`diagnostics/orchestrator.py`): seleciona
   analyzers pelo `SourceType` do request, executa em ordem
   determinística de registro, cronometra `duration_ms` real, e converte
   exceção de analyzer em *limitação do relatório* — um analyzer quebrado
   nunca derruba o diagnóstico.
2. **Contexto entre analyzers via request, não via import**: sinais de
   workload (`ExecutionContext.extra["workload_*"]`) e metadados fluem
   pelo contrato. Nenhum analyzer importa outro — acoplamento zero e
   testabilidade isolada preservadas.
3. **Render é camada separada** (`reporting/render.py`): analyzers emitem
   `AnalysisResult`; o orquestrador monta `DiagnosticReport`; renderers
   terminal/JSON/Markdown consomem o report. Apresentação nunca mora em
   analyzer.
4. **API/MCP como contratos**: `api/contracts.py` define os shapes; um
   teste de readiness os mantém coerentes com os contratos públicos.
   Nenhum servidor neste ciclo (decisão do Grill Gate) — Cycle 03+ pode
   expor FastAPI/MCP sobre o orquestrador sem tocar analyzers.

## Consequências

- Novos analyzers entram só por `registry.register` — orquestrador,
  renderers e CLI não mudam.
- Falhas parciais são visíveis (limitações), não silenciosas.
- Markdown/JSON saem do mesmo `DiagnosticReport` — sem divergência de
  conteúdo entre formatos.
- `DiagnosticReport.recommendations` foi adição retrocompatível
  (schema segue `1.0.0`, minor aditivo — ADR 0002).

## Alternativas rejeitadas

- Pipeline encadeado (output de um analyzer vira input do próximo):
  introduziria ordem implícita e acoplamento; o modelo request+contexto
  cobre os casos reais.
- Servidor FastAPI já neste ciclo: o Grill Gate decidiu contratos+
  readiness apenas — evita superfície não-homologada.
