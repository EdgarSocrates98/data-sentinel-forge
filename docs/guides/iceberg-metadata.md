# Guia — Metadados Iceberg

Entrada: `metadata.json` exportado (Glue Catalog, arquivo local, conector
autorizado). O analisador **nunca segue URLs** — `location`/`manifest-list`
são lidos como referências textuais.

```bash
data-sentinel lakehouse metadata -f metadata.json
data-sentinel lakehouse metadata -f metadata.json --json
```

## O que é diagnosticado

- Versões de formato 1/2/3; campos desconhecidos são preservados e
  reportados como limitação (não inventados).
- `current-snapshot-id` inconsistente → CONFIRMED (DATA_QUALITY).
- Evolução de schema (field-ids renomeados/re-tipados) → COMPATIBILITY.
- Evolução de partições; transform `void` → COMPATIBILITY.
- Small files: **condicional** — só quando summaries declaram contagem e
  tamanho; status POSSIBLE, nunca threshold universal.
- Retenção ausente com muitos snapshots → POSSIBLE.
- Snapshot-log crescido → CONFIRMED custo.

## Limites de segurança

16MB máx., profundidade 64, 10k snapshots. Malformado → limitation +
UNKNOWN (nunca crash nem causa fabricada).

## Não faz

Não baixa manifests/tabelas, não repara snapshots, não executa
expire/rewrite — recomendações são decisões de engenharia.
