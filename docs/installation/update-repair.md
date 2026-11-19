# Update & Repair

## Update / reinstall

```bash
data-sentinel install --yes   # idempotente — arquivos idênticos são adotados
```

Reinstall sobre instalação existente é no-op limpo: o receipt reporta a
contabilidade incremental em `counts` — arquivos byte-idênticos saem como
`unchanged`/`adopted` e `written`/`written_bytes` ficam `0` (arquivos
gerenciados não são re-tocados).

## Repair

```bash
data-sentinel install repair --dry-run   # preview
data-sentinel install repair             # restaura managed files
```

Repair restaura arquivos gerenciados corrompidos/ausentes a partir dos
assets da wheel (byte-identical). Arquivo modificado pelo usuário que
nunca foi do ledger → recusado, nunca clobbered.
