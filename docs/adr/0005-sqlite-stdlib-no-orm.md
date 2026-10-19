# ADR 0005 — SQLite + migrations com stdlib, sem ORM

**Status:** accepted
**Data:** Cycle 01 (ds-0007)

## Contexto

O produto exige persistência local offline para relatórios e evidências, sem
infraestrutura de servidor e com dependências mínimas.

## Decisão

- `sqlite3` da stdlib com `SentinelStore`; sem ORM, sem dependência extra.
- Migrations numeradas em `persistence/migrations/NNNN_desc.sql`, aplicadas
  transacionalmente e registradas em `schema_migrations` — append-only.
- Serialização via `DiagnosticReport.to_json()`/`from_json()` — a tabela
  guarda o documento do contrato, não uma decomposição ORM paralela.
- Diretório do store criado com `0700` em POSIX; journal WAL.
- Evidências são re-sanitizadas na escrita (defesa em profundidade).

## Consequências

- Zero dependências novas; schema auditável em SQL puro.
- Queries são SQL explícito com valores sempre parametrizados — nenhuma
  interpolação de dados do usuário.
- O documento JSON preserva fidelidade total do contrato (round-trip testado
  com `==` no modelo Pydantic).
