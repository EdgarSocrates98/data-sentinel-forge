# Cycle 03 — Relatório Final

- SHA auditado: `90c10a8b703a67b7ced408e86992b71a16765ce4` (main pré-C03)
- Escopo: `prompt_evo_cycle3.md` — Iceberg, Lake Formation, FGAC/FTA,
  cross-account, IAM/S3/KMS, MERGE/APPEND, knowledge base, CLI/reporting
- Specs: ds-0020..ds-0029 (10), todos arquivados com verificação + review

## Decisão

## APPROVED WITH RESTRICTIONS

Restrições (todas herdadas ou declaradas explicitamente):

1. **Homologação AWS real = BLOCKED** — ambiente sem credenciais
   (`~/.aws` ausente, boto3 → None). Gate `DATA_SENTINEL_AWS_TESTS=1`
   verificado nos dois sentidos: allowlist read-only passa, chamada real
   falha `NoCredentialsError`. Guia de execução manual publicado.
2. **CI remota bloqueada por billing** — repo privado, jobs não iniciam;
   comandos equivalentes passam localmente (herdado do C02).
3. **API/MCP ausentes** — fora de escopo por desenho (C02).
4. **Windows/macOS** — só via CI (bloqueada).
5. Simulação IAM não usada por padrão — limitações documentadas.

## Feature matrix

| Capacidade | Estado | Evidência |
|---|---|---|
| Iceberg metadata v1/v2/v3 | entregue | 22 testes, guards §3.8, fixtures |
| Snapshots/evolução/small files | entregue | condicional, DECLARED, nunca fabricado |
| Knowledge base YAML | entregue | 10 regras no wheel, venv limpa validada |
| Compat engine | entregue | 12 testes, wildcards/conflitos/UNKNOWN |
| Cross-account + grafo | entregue | 7 arestas c/ proveniência, 9 testes |
| IAM/S3/KMS offline | entregue | 15 testes, deny>allow>unknown |
| MERGE/APPEND/DDL | entregue | 10 testes, sqlglot, nunca executa |
| Resolver + CLI + reporting | entregue | 5 comandos, 10 testes |
| Golden/security/bench/E2E | entregue | 26 golden, 10 sec, benchmarks JSON, A–F |
| AWS real | **BLOCKED** | sem credenciais — guia §12 |

## Números

- 488 testes, 3 skipped (env-gated), ~15.5s
- ruff clean, mypy strict 90+ arquivos, cobertura acompanhada
- 10 analyzers registrados no doctor
- Benchmarks: metadata 5000 snapshots = 37ms/6.6MB pico; select 10k = 90ms

## Achados reais corrigidos no ciclo

- `_listify` IAM descartava escalares não-string (policy malformada virava
  silêncio) — corrigido para stringificar.
- Wildcard `operation:"*"` somava especificidade → empates espúrios —
  corrigido, wildcard não pontua.
- Constraints duplicadas no compat (matrix+mode) — dedup.
- Quadrático `_STAT_KV` (herança C02) já corrigido no ciclo anterior.

## Dívidas técnicas

- `AnalysisResult` não carrega `OptimizationRecommendation` — recs vivem
  em `Finding.recommendations` (P2).
- Grafo de permissões não cobre ainda todos os nós (bucket/kms como nós
  só quando contexto declara) (P2).
- Nenhum P0/P1 aberto.

## Prontidão Cycle 04

Backlog natural: conectores read-only Lake Formation/IAM/S3/KMS reais
(allowlist já no padrão), resolver consumindo conectores quando
credenciais existirem, API/MCP servers sobre os mesmos analyzers,
schema_version bump somente se contratos quebrarem.
