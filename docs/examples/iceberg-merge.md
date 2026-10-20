# Exemplo — MERGE com duplicidade controlada

Cenário D: MERGE INTO com `stats.source_duplicate_keys = 1400` declarado.

```bash
data-sentinel lakehouse operation -f fixtures/operations/merge_dups.json
```

Finding real:

```
[MEDIUM/CONFIRMED] data_quality
  1400 chaves duplicadas na fonte do MERGE — Iceberg falha com ambiguity
  ou aplica update imprevisível por linha.
  evidência: fixtures/operations/merge_dups.json
    stats declaram 1400 chaves-fonte duplicadas no merge source
  recomendação: Resolver duplicidade ANTES do merge (janela/dedup
    determinística na fonte) — nunca deduplicar o alvo automaticamente.
```

Contrastes importantes:

- `stats.source_key_unique: true` → nenhum finding de unicidade.
- Sem stats → `UNKNOWN`: "Unicidade da chave-fonte do MERGE não declarada".
- ON com OR → `POSSIBLE` ambiguidade, nunca CONFIRMED.
