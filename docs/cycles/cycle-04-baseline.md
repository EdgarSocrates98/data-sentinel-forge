# Cycle 04 Baseline

Baseline SHA: `e67d8a6` (HEAD após Cycle 03.1, pushed).

## Auditoria por ciclo

| Ciclo | Estado | Números |
|---|---|---|
| C01 Foundation | arquivado ds-0001..0009 | base src-layout, contratos, CLI |
| C02 AWS/Spark/SQL | arquivado ds-0010..0019 | conectores read-only, plan/join, orquestrador |
| C03 Lakehouse | arquivado ds-0020..0029 | Iceberg, compat, cross-account, IAM, ops |
| C03.1 Convergence | arquivado ds-0030..0039 | boundaries, interop (import), incident graph, eval real |

## Estado atual

- 530 testes, 3 skips env-gated; ruff+mypy strict limpos.
- 10 analyzers + adapters/doctor + incident graph + 12 descriptors.
- Contratos: entities v1.0.0 + lakehouse + interop 1.0.0 + quality (novo).
- CI remota: BLOCKED billing (verificado runs 39411265586).
- AWS real: BLOCKED sem credenciais.
- Doctor repos: read-only; interop import-only até este ciclo.

## Drift documental

- docs/cli.md: seções `import` e `capabilities --descriptors` já
  adicionadas no C03.1 — sem drift detectado.
- README: comandos atualizados C03.1.
- Nenhum drift corrigível encontrado nesta auditoria.

## Ciclo 04 — escopo

Data Quality contracts, adapters (parse de resultados), profiling/drift
(numpy/scipy extra [stats]), OpenLineage (Marquez real se possível),
lineage graph + impact, Doctor export, CLI, E2E A–H.
