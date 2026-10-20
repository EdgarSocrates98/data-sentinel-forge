# Cycle 03 — Arquitetura

Fluxo implementado (§2.3):

```
Diagnostic Request
       v
Lakehouse Context Resolver (lakehouse/resolver.py)
       +-- Glue metadata (connectors/aws — C02)
       +-- Iceberg metadata (analyzers/iceberg)
       +-- Lake Formation / access context (analyzers/crossaccount)
       +-- IAM/S3/KMS (analyzers/iam)
       +-- Operações MERGE/APPEND (analyzers/operations)
       v
Compatibility Engine (knowledge/compat.py)
       +-- regras YAML empacotadas (knowledge/rules/*.yaml)
       v
Evidence → Analyzer findings → DiagnosticReport
       +-- CLI `lakehouse` | JSON | Markdown
```

## Componentes

| Módulo | Função |
|---|---|
| `analyzers/iceberg/` | parser metadata v1/v2/v3 + findings (snapshots, schema/spec evolution, small files, retenção) |
| `knowledge/` | schema de regras YAML + engine de seleção + `assess_compatibility` |
| `analyzers/crossaccount/` | grafo de permissões (7 nós/arestas, proveniência por aresta) |
| `analyzers/iam/` | parser de policies + avaliador offline + contexto S3/KMS |
| `analyzers/operations/` | MERGE/APPEND/DDL via sqlglot — nunca executa |
| `lakehouse/resolver.py` | agrega resultados num `LakehouseContext` único |
| `cli` grupo `lakehouse` | metadata/access/policy/operation/compat |

## Invariantes

- Toda evidência Iceberg/knowledge é `DECLARED` — metadados não são
  métricas de execução.
- `UNKNOWN`/`NOT_VERIFIED` nunca são `UNSUPPORTED`.
- Ausência de visibilidade → aresta `unverified`, nunca negação.
- Suporte nunca generalizado entre versões de runtime.
- Nenhuma operação mutadora: sem DML, sem decrypt, sem snapshot repair.
