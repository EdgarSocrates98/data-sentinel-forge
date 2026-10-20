# Guia — Lake Formation FGAC/FTA

Modos de acesso em Glue+Iceberg: `iam` (identity policies), `fgac`
(fine-grained: tabela/coluna/row via grants LF), `fta` (full table access),
`legacy`, `unknown`. O motor **nunca presume FGAC** — modo desconhecido
rebaixa o veredito e gera constraint explícita.

```bash
data-sentinel lakehouse compat --runtime glue-5.1 --operation select \
    --access-mode fgac --table-format iceberg
```

## Regras-chave (knowledge base)

- `glue51-lakeformation-fgac`: SUPPORTED_WITH_CONSTRAINTS — column-level
  read ≠ write; MERGE/UPDATE/DELETE exige FTA ou grants amplos.
- `glue40-lakeformation-fgac-iceberg`: UNKNOWN — não verificado nesta base.
- Ausência de grant visível → UNKNOWN (nunca negação).

FGAC read column-level não implica write. Grants cross-account são
avaliados por elo (origem/destino separados).
