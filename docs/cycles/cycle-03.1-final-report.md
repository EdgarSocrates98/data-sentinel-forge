# Data Sentinel — Cycle 03.1 Final Report

Doctor Convergence, Operational Differentiation & Ecosystem Interoperability.

## Baseline

- SHA main de entrada: `7510b7557fb9d78b7116522a6236ea1be25a6408`
- Repos auditados: forge-doctor-data `266e789a`, forge-doctor-api `8912f3b2`
- Specs: ds-0030→ds-0039 (10), todos arquivados com review.

## Matriz de sobreposição — VERIFIED

`docs/audits/doctor-sentinel-audit.md` — inspeção de código real +
execução real do Doctor (scan + handoff). Resumo:

- Doctor-only: auditoria de projeto/repo (REP/PY/DEP/GIT/CI), baseline/
  histórico, remediation plans, ~344 checks estáticos.
- Sentinel-only: telemetria operacional, timeline, grafo de evidência,
  correlação cross-source, avaliador IAM offline, compat de execução.
- Overlap justificável: Glue/Iceberg compat, FGAC/LF, MERGE, skew —
  ângulos estático vs operacional.
- Doctor-API: zero overlap de checks; mesmo contrato de interop.

## Boundary architecture — VERIFIED

`docs/architecture/domain-boundaries.md` + ADR 0012: fronteira por tipo
de evidência (STATIC/CONFIG vs OBSERVED/DECLARED), overlap classificado,
realocações em backlog (nada removido).

## Contratos adicionados — VERIFIED

- `core/contracts/interop.py`: ExternalDiagnosticBundle (envelope 1.0.0),
  InteropFinding/Evidence/Entity/Relationship/Capability/UnknownFact/Plan,
  ToolRef, IntegrityMetadata, CapabilityDescriptor.
- Vocabulário `forge-contracts/1` (adotado, não reinventado).
- `schemas/ExternalDiagnosticBundle.schema.json` +
  `schemas/CapabilityDescriptor.schema.json` exportados.

## Adapters implementados — VERIFIED

`adapters/doctor/`: detecta 3 formatos reais (handoff-bundle@1,
forge-contracts/1, scan-json@3.0), normaliza, converte para Finding/
Evidence internos. Safety: ≤20MB, JSON-only, sem exec, sem rede, sem
Doctor instalado, segredos redigidos, unknowns preservados, findings
nunca auto-CONFIRMED. CLI: `import doctor-bundle -f`.

## Operational intelligence — VERIFIED

- `UnifiedExecutionContext`: 16 campos, ausente→UNKNOWN.
- `EvidenceGraph`: 10 nós / 9 arestas; causal vs associação separados;
  vínculo justificável obrigatório; imported→nunca causal.
- Timeline multi-fonte: timestamps reais, gaps >120s declarados,
  granularity_notes.
- `capabilities --descriptors`: 12 descriptors para orquestradores.

## Resultados E2E — VERIFIED

530 testes (era 488 na entrada): +42 novos (interop contract 8, adapter
13, incident/timeline 14, descriptors 3, evaluation gate 2, e2e interop 2).
Golden 26 + E2E A–F sem regressão. ruff+mypy strict limpos.

## Medições de complementaridade — VERIFIED

`docs/evaluations/complementarity-results.json` (execução real,
doctor 1.0.3 venv separada): doctor 4 aplicáveis/2 detecções; sentinel
9/6 + 3 UNKNOWNs corretos; interop union 713, dup ~0.7%; 0 chamadas
externas; doctor 2.409s vs sentinel 0.14s.

## Gaps encontrados

- Doctor não cobre telemetria (esperado — fronteira).
- Doctor-API sem checks data-eng (esperado — outro domínio).
- s04/s05 produzem UNKNOWN correto — ground truth inicial era otimista;
  contados corretamente no relatório.

## Regressões corrigidas

Nenhuma regressão de código — 2 ajustes de robustez descobertos pela
suíte: import circular timeline↔analyzers (TYPE_CHECKING), campo
`evidence` string no fixture canônico (tipo união).

## Resultados de segurança — VERIFIED

Bundle malicioso tratado como dados inertes (path traversal, XXE-like,
código embutido — teste prova não-execução); cap de tamanho; sem network
no adapter; segredos redigidos; `test_no_forge_imports_in_src`.

## Resultado da CI — VERIFIED-BLOCKED

Runs 39344194655/39351536029/39407932763 falham em 8-9s SEM steps —
bloqueio de billing da conta (repo privado), não de código. Comandos
equivalentes do workflow passam localmente.

## Dívida técnica

- P0: nenhuma.
- P1: CI remota depende de billing (infra); conhecimento de versões
  duplicado Doctor×Sentinel (mitigar via consumo de capabilities).
- P2: export direction do bundle (trivial, adiado); knowledge pack
  compartilhado (reavaliar C04); eval dup_estimate é heurística simples.

## Limitações conhecidas

- Interop é import-only neste ciclo (decisão de grill).
- Avaliação usa 10 cenários sintéticos — não é benchmark de precisão
  em produção.
- `dup_estimate` por categoria×texto é conservador/grosseiro.
- AWS real segue BLOCKED sem credenciais (herdado).

## Backlog Cycle 04

1. Export direction do bundle (Sentinel→Doctor/Forge).
2. Consumo de Doctor capability-report como entrada (R2).
3. Knowledge pack compartilhado — reavaliar com crescimento das regras.
4. Cenários de avaliação com corpus real anonimizado.
5. CI remota: desbloquear billing ou runner self-hosted.
6. MCP/API server (readiness existe; servidor não).

## Status de aprovação

**APPROVED WITH RESTRICTIONS**

- 15/16 critérios §11 VERIFIED; critério 15 (CI) VERIFIED-BLOCKED por
  causa externa (billing) — comandos equivalentes verdes localmente.
- Integração validada com fixtures + execução real do Doctor local —
  não com Doctor em produção/CI (declarado, não exagerado).

Seções §12: VERIFIED (contratos/adapter/grafo/eval/tests), BLOCKED (CI
remota, AWS real), NOT_TESTED (interop em produção, export direction).
