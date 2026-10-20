# Exemplo — Iceberg cross-account

Cenário B/C: job na conta 111111111111 acessando `sales.orders` na conta
702561771161 via resource link.

```bash
data-sentinel lakehouse access -f fixtures/access/cross_write.json --quiet
# 2 achado(s): POSSIBLE=1, UNKNOWN=1
```

Findings reais:

- `POSSIBLE` — "Escrita cross-account 'merge' exige cadeia completa:
  leitura na origem + grant de escrita no destino + catálogos alinhados +
  S3/KMS das DUAS contas."
- `UNKNOWN` — grants LF parcialmente invisíveis; ausência de visibilidade
  não é negação.

O grafo de permissões (metadados do resultado) marca `SHARES_WITH` como
`unverified` até que grants sejam exportados — nunca confirma
compartilhamento que não foi observado.

Para elevar confiança, exporte `ListPermissions`/`GetTableObjects` da conta
de destino e alimente `observed_permissions`.
