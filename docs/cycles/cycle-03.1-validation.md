# Cycle 03.1 — Validation Matrix

| # | Critério de aceite (§11) | Status | Evidência |
|---|---|---|---|
| 1 | Matriz fundamentada em código real | VERIFIED | `docs/audits/doctor-sentinel-audit.md` — execução real do doctor 1.0.3 + inspeção de fonte |
| 2 | Responsabilidades documentadas | VERIFIED | `docs/architecture/domain-boundaries.md` + ADR 0012 |
| 3 | Contrato de interop versionado | VERIFIED | `core/contracts/interop.py`, `INTEROP_SCHEMA_VERSION=1.0.0`, schemas exportados |
| 4 | Sentinel importa bundles válidos | VERIFIED | adapter + 13 testes; import real de 73 findings do handoff |
| 5 | Integração opcional | VERIFIED | `adapters/` é import-optional; suite passa sem Doctor; teste `test_no_forge_imports_in_src` |
| 6 | Sem dependências cíclicas | VERIFIED | zero imports `forge_*` em src/; import circular interno corrigido (timeline TYPE_CHECKING) |
| 7 | Proveniência preservada | VERIFIED | imported→Evidence DECLARED + `importado:<producer>`; nunca CONFIRMED (testes) |
| 8 | Offline funcional | VERIFIED | 530 testes sem rede; evaluation externals=0 |
| 9 | Análise independente de LLM | VERIFIED | nenhum LLM em src/ nem no adapter |
| 10 | E2E passam | VERIFIED | E2E A–F (26 golden + e2e) + novo e2e_interop — 530 total |
| 11 | Sem regressão C01–C03 | VERIFIED | 488→530 testes, todos verdes |
| 12 | Wheel com recursos | VERIFIED | rules YAML + schemas + fixtures empacotados (hatch inclui src tree) |
| 13 | Docs refletem funcionalidades reais | VERIFIED | guias escritos contra comandos executados de verdade |
| 14 | Complementaridade com evidências | VERIFIED | `docs/evaluations/complementarity-results.json` status VERIFIED (10 cenários reais) |
| 15 | CI verificada ou desconhecida | VERIFIED-BLOCKED | runs verificados: billing bloqueia jobs (8s sem steps) — infra, não código |
| 16 | Nada removido sem migração | VERIFIED | só adições: +6 src files, +5 test files, +docs/fixtures |

Legendas: VERIFIED = provado por execução; VERIFIED-BLOCKED = verificado
como bloqueado por causa externa.
