# Cycle 04 — Final Report

**Decisão: APPROVED WITH RESTRICTIONS**

## Entregue (10 specs, todos arquivados com review)

| Spec | Entrega | Verificação |
|---|---|---|
| ds-0040 | Contratos quality.py + 8 schemas JSON + baseline | 539 testes |
| ds-0041 | Parser §3.2 YAML/JSON + validação + versionamento | 549 |
| ds-0042 | Adapters parse-only (PyDeequ/Deequ/GE/SQL/DataFrame) | 557 |
| ds-0043 | Profiling + drift (numpy/scipy extras, fallback) | 567 |
| ds-0044 | OpenLineage ingestion + fixture REAL Marquez | 7 testes |
| ds-0045 | Grafo + impacto potencial-only | 7 testes |
| ds-0046 | Export DiagnosticReport → forge-contracts/1 + round-trip | 3 testes |
| ds-0047 | CLI quality/lineage/export + integrity | 6 testes |
| ds-0048 | E2E A–H + segurança + benchmarks reais | 606 |
| ds-0049 | Docs, matriz, backlog Cycle 05 | — |

**Total: 606 testes, 3 skips env-gated, ruff+mypy strict limpos.**

## Destaques
- **Fixture real, não simulado**: `marquez-real.jsonl` foi round-tripped
  num Marquez Docker real (201s + GET /jobs confirmado).
- **Round-trip interop bidirecional provado**: export do Sentinel é
  reimportado pelo próprio adapter — não só shape compatível.
- **Regras duras mantidas**: missing→UNKNOWN; safe_load only;
  potencial_only=True sempre; sem execução de engines.

## Restrições declaradas
1. Engines de qualidade não executadas — somente parse de exportações
   (decisão Grill Gate, não limitação acidental).
2. Drift sem scipy = heurística PSI/TV com limitation explícita.
3. Impacto = alcançabilidade de grafo (dataset-level), nunca prova.
4. CI remota segue **BLOQUEADA por billing** (repo privado, jobs não
   iniciam). Comandos do CI passam localmente.
5. AWS real: sem credenciais neste ambiente (igual Cycle 03).
6. Linhagem coluna-a-coluna não filtra impacto — backlog C05.

## Benchmarks reais (docs/evidence/benchmarks-cycle4.json)
| Operação | Tempo |
|---|---|
| parse contrato 200 regras | 33.4 ms |
| normalize 5k observações | 42.5 ms |
| profile 50k valores | 43.5 ms |
| drift 10k×10k | 4.5 ms |
| grafo 1k eventos | 23.7 ms |
