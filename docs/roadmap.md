# Roadmap

Visão por ciclo conforme o plano mestre (`prompt_inicial.md`).

Estados: **entregue** / **entregue com restrições** / **em desenvolvimento** /
**planejamento**. Histórico de decisões preservado abaixo.

## Cycle 02 — Spark & Glue Intelligence — ENTREGUE COM RESTRIÇÕES

Entregue (ds-0010..0019): conectores AWS read-only (Glue, CloudWatch),
analyzer de plano físico, join intelligence, SQL v0.2 (AST/dialetos),
config advisor, orquestrador, CLI grupos, Markdown, contratos API/MCP.
Restrições: AWS validado com mocks/Stubber (não real), Windows/macOS só
via CI (bloqueada por billing), API/MCP sem servidor.
Ver `docs/cycles/cycle-02-final-report.md`.

## Cycle 03 — Iceberg, Lake Formation & Security — EM DESENVOLVIMENTO

Escopo (`prompt_evo_cycle3.md`): Iceberg metadata intelligence, knowledge
base de compatibilidade versionada, engine Glue/FGAC/FTA, diagnóstico
cross-account, IAM/S3/KMS read-only, MERGE/APPEND intelligence, CLI e
reporting lakehouse. Specs ds-0020..ds-0029.

## Cycle 04 — Data Quality & Lineage

Contratos declarativos de qualidade, análise de impacto e lineage entre
datasets/jobs.

## Cycle 05 — Agentic Intelligence

Runtime agêntico controlado sobre as evidências determinísticas: planejamento,
memória, orçamentos de token/tool-call (campos já reservados na config),
agentes especialistas com responsabilidades delimitadas.

## Cycle 06 — Sentinel Control Center

Interface Angular para investigação, exploração e observabilidade, com
design system próprio.

## Cycle 07 — Autonomous Operations

Análise histórica (duração, tendências), alertas preventivos e operações
assistidas — sempre com autorização explícita antes de qualquer escrita.

## Cycle 08 — Production, Benchmarks & Open Source

Hardening, testes de carga/concorrência, benchmarks medidos (nunca inventados)
e preparação para adoção externa.

---
