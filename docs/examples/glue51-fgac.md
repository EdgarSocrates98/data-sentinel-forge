# Exemplo — Glue 5.1 + FGAC + Iceberg + MERGE

Cenário A do E2E: job Glue 5.1 lendo tabela Iceberg via Lake Formation FGAC
e executando MERGE com fonte que tem duplicidade declarada.

```bash
data-sentinel lakehouse compat --runtime glue-5.1 --operation merge \
    --access-mode fgac --table-format iceberg
```

Saída real:

```
status: SUPPORTED_WITH_CONSTRAINTS
runtime=glue-5.1 formato=iceberg modo=fgac op=merge
  - Glue 5.1 mantém suporte LF FGAC para Iceberg com mesmas restrições de 5.0...
  - MERGE/UPDATE/DELETE via FGAC exige full table access no grant LF ou ALL...
  ref: https://docs.aws.amazon.com/lake-formation/latest/dg/workloads-glue.html
```

Depois, a operação MERGE em si (envelope com stats declaradas):

```bash
data-sentinel lakehouse operation -f fixtures/operations/merge_dups.json --quiet
# 2 achado(s): CONFIRMED=1, UNKNOWN=1
```

Leitura: compatível **com restrições** (FGAC read ≠ write), e a fonte
duplicada é CONFIRMED porque `stats.source_duplicate_keys` foi declarada —
sem estatística, o veredito seria UNKNOWN, nunca afirmado.
