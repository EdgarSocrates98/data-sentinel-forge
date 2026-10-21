# Roadmap

Visão por ciclo. Estados: **entregue** / **entregue com restrições** /
**em desenvolvimento** / **planejamento**. Cada ciclo cita seu relatório
final em `docs/cycles/`.

## Cycle 02 — Spark & Glue Intelligence — ENTREGUE COM RESTRIÇÕES

Conectores AWS read-only (Glue, CloudWatch), analyzer de plano físico,
join intelligence, SQL v0.2 (AST/dialetos), config advisor, orquestrador,
CLI grupos, Markdown, contratos API/MCP. Restrições da época: AWS
validado com mocks/Stubber, Windows/macOS só via CI. Ver
`cycle-02-final-report.md`.

## Cycle 03 — Iceberg, Lake Formation & Security — ENTREGUE

Iceberg metadata intelligence, knowledge base de compatibilidade
versionada, engine Glue/FGAC/FTA, diagnóstico cross-account, IAM/S3/KMS
read-only, MERGE/APPEND intelligence, CLI e reporting lakehouse.
Specs ds-0020..ds-0029. Ver `cycle-03-final-report.md`.

## Cycle 03.1 — Doctor×Sentinel Convergence — ENTREGUE

Boundaries, interop (`import doctor-bundle`), incident graph,
capability discovery, avaliação de complementaridade. Ver
`cycle-03.1-final-report.md`.

## Cycle 04 — Data Quality & Lineage — ENTREGUE

Contratos declarativos de qualidade, análise de impacto e lineage entre
datasets/jobs. Ver `cycle-04-final-report.md`.

## Cycle 05 — Agentic Intelligence — ENTREGUE

Runtime agêntico controlado sobre evidências determinísticas: registry
de especialistas, tools MCP (20), orçamentos, investigação orquestrada
(`investigate run`). Ver `cycle-05-final-report.md` e
`cycle-05-1-final-report.md`.

## Cycle 06 — Sentinel Control Center — ENTREGUE

API FastAPI (`serve`, `/api/v1/*`) + Control Center Angular 20
(`frontend/`): investigações, evidence graph, workloads, relatórios.
Ver `cycle-06-final-report.md`.

## Cycle 07 — Autonomous Operations — ENTREGUE

Análise histórica, tendências, watches, regressões e remediação
assistida — com autorização explícita antes de qualquer escrita.
Persistência SQLite (`~/.data-sentinel/sentinel.db`). Ver
`cycle-07-final-report.md`.

## Cycle 08 — Production, Benchmarks & Open Source — ENTREGUE COM RESTRIÇÕES

- **08** — hardening, CI multiplataforma (Linux/macOS/Windows ×
  Python 3.11/3.12), benchmarks medidos, docs públicas. Ver
  `cycle-08-final-report.md`.
- **08.1** — independência total (core offline, sem The Forge/AI externa),
  cobertura E2E, segurança. Ver `cycle-08-1-final-report.md`.
- **08.2** — instalador portátil (`data-sentinel install`), adapters de
  host (Claude/Devin/Codex/Copilot; Cursor parcial), 5 skills + 3 agents
  no catálogo, MCP lifecycle, `install env`, integridade SHA-256.
  Restrições: PyPI não publicado, Cursor sem adapter completo,
  integração The Forge limitada a manifests. Ver
  `cycle-08-2-final-report.md`.

## Próximos passos (backlog conhecido)

- Publicação PyPI (workflow `release.yml` preparado com Trusted
  Publishing, gated por aprovação humana).
- Adapter completo de Cursor; integração The Forge além de manifests.
- LOWs documentados no §27 do relatório do Cycle 08.2.
