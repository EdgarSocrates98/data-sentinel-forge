# Roadmap

Visão por ciclo conforme o plano mestre (`prompt_inicial.md`). Cycle 01 está
entregue; os demais são planejamento — **nada abaixo existe ainda**.

## Cycle 02 — Spark & Glue Intelligence

Primeiro conjunto avançado de capacidades diagnósticas: connector AWS Glue
read-only (boto3, como extra opcional), análise de métricas/logs CloudWatch,
comparação entre execuções e diagnóstico de configuração de jobs.

## Cycle 03 — Iceberg, Lake Formation & Security

Diagnóstico profundo de lakehouse AWS: snapshots Iceberg, permissões Lake
Formation, catálogo e drift de tabelas.

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

## Backlog priorizado do Cycle 02 — candidatos a spec

Ordem sugerida para `factory/specs/inbox/`:

1. **ds-0010 — AWS Glue connector (read-only)**: extra opcional `[glue]` com
   boto3; listar jobs/runs/configs; respeitar `allow_network=false` no perfil
   offline; erros de credencial como `ConfigurationError` amigável.
2. **ds-0011 — CloudWatch log fetch (opt-in)**: recuperar log de um run
   autorizado e alimentar o `SparkGlueLogAnalyzer` existente — sem polling
   contínuo.
3. **ds-0012 — Run comparison**: comparar duas execuções (duração, findings,
   config diff) reaproveitando `list_reports` do store.
4. **ds-0013 — Spark event log / Spark UI metrics**: estender evidência além
   de texto de log (stage metrics, spill quantificado).
5. **ds-0014 — Glue config diagnostics**: regras sobre job config (workers,
   timeout, retries) combinadas com findings de log.
6. **ds-0015 — Report diff/trend básico**: séries temporais mínimas sobre
   relatórios persistidos (preparação do Cycle 07).

Critério de entrada no Cycle 02: cada spec mantém os princípios — evidência
obrigatória, offline funcional sem credenciais, read-only sem autorização.
