# Guia — MERGE/APPEND incremental

```bash
data-sentinel lakehouse operation -f merge.sql
data-sentinel lakehouse operation -f envelope.json   # {sql, stats, log}
```

## MERGE

- ON ausente → CONFIRMED risco de match ambíguo.
- ON com OR → POSSIBLE ambiguidade.
- `stats.source_duplicate_keys` > 0 → CONFIRMED duplicidade (com
  quantidade); dedup é na FONTE, nunca no alvo.
- Sem `stats.source_key_unique` → UNKNOWN sobre unicidade.
- WHEN MATCHED/NOT MATCHED contados; semântica nunca alterada.

## APPEND / INSERT

- INSERT INTO → POSSIBLE risco de reprocessamento sem idempotência.
- INSERT OVERWRITE → declarado, sem risco de duplicata por retry.
- UPDATE/DELETE sem WHERE → CONFIRMED full-table.

## Commit conflicts

`stats.log`/`log` com `CommitFailedException`,
`ConcurrentModificationException` → CONFIRMED; retry só se idempotente.

SQL é parseado (sqlglot), **nunca executado**.
