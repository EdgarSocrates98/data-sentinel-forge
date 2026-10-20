# Guia — Diagnóstico cross-account

Entrada: JSON `AccessContext` — contas, região, catálogo, database, table,
resource link, lf_mode, `required_operation`, `observed_permissions`,
`unknown_permissions`.

```bash
data-sentinel lakehouse access -f contexto.json
```

## Grafo de permissões

Nós: account, principal, catalog, database, table, resource_link.
Arestas: ASSUMES_ROLE, REFERENCES, SHARES_WITH, GRANTED_ON, READS_FROM,
WRITES_TO, ENCRYPTED_BY — cada uma `observed|declared|inferred|unverified`.
Arestas unverified viram limitations.

## Cenários

- Leitura cross-account sem grants observados → UNKNOWN + checklist.
- Escrita → POSSIBLE com cadeia: origem, destino, catálogos, S3, KMS.
- Conta origem = destino → análise reverte a single-account.

## Homologação real (§12) — execução manual

Ambiente sem credenciais = BLOCKED. Para homologar:

1. Configure credenciais read-only não-prod (perfil ou env vars).
2. `export DATA_SENTINEL_AWS_TESTS=1`
3. `uv run pytest tests/e2e -k AwsReal -v`
4. Registre conta/região/data no relatório — fixtures nunca são
   apresentadas como recursos reais.
