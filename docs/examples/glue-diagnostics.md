# Exemplo — Diagnóstico de job Glue

Cenário: um job Glue falhou e queremos metadados + logs + correlação.
O conector é read-only e requer `[aws]` + credenciais — aqui mostramos o
fluxo real e o comportamento honesto quando não há AWS.

## 1. Inspecionar o job (read-only)

```bash
data-sentinel glue inspect --job etl-vendas --region us-east-1
```

Retorna definição do job com `DefaultArguments` **sanitizados**
(chaves sensíveis viram `«redacted:arg»`).

## 2. Listar runs

```bash
data-sentinel glue runs --job etl-vendas --limit 10 --region us-east-1
```

Paginação limitada: 1 chamada por página de 50 runs (ver benchmark
`aws_calls_per_paginated_run_listing` em `docs/evidence/benchmarks.json`).

## 3. Diagnosticar uma run específica

```bash
data-sentinel glue diagnose --job etl-vendas --run-id jr_abc123 --region us-east-1
```

Pipeline: `GetJobRun` → janela de log CloudWatch → parser de eventos →
correlação de exceções → timeline → analyzer de padrões → relatório.

## Sem credenciais — recusa limpa (saída real)

```text
$ data-sentinel glue diagnose --job demo-job --run-id jr_demo --region us-east-1
erro: glue:get_job_run: credenciais indisponíveis — configure
profile/env/IAM role/SSO [aws.sem_credenciais]
```

## Equivalente offline

O mesmo analyzer de log roda sobre artefatos locais sem nenhuma
credencial — evidência real em `docs/evidence/cycle2/analyze-glue-oom.txt`:

```bash
data-sentinel analyze --file fixtures/logs/glue_oom.log --platform aws_glue
```

## Restrição declarada

Todo o código AWS deste ciclo foi **validado com mocks/Stubber, não com
AWS real** — incluindo paginação, throttling e erros IAM. Um teste
opcional contra AWS real existe gated por `DATA_SENTINEL_AWS_TESTS=1`
(skipped por padrão; requer credenciais não-prod).
