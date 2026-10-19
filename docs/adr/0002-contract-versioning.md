# ADR 0002 — Contract versioning strategy

**Status:** accepted
**Data:** Cycle 01 (ds-0002)

## Contexto

Relatórios de diagnóstico são artefatos persistidos e potencialmente
compartilhados; consumidores precisam saber qual versão de schema produziu um
documento.

## Decisão

- `DiagnosticReport.schema_version` carrega `SCHEMA_VERSION = "1.0.0"`
  (semver), definida em `core/contracts/entities.py`.
- Contratos são Pydantic v2 em `core/contracts`, separados de tipos internos.
- JSON Schemas são exportados para `schemas/` por `scripts/export_schemas.py`
  e validados em teste de contrato.
- Mudanças: campos novos opcionais = minor; campos removidos/renomeados ou
  mudança de tipo = major; valores de enum novos = minor com documentação.

## Consequências

- Relatórios antigos continuam validáveis; a leitura rejeita com erro de
  validação Pydantic claro quando incompatível.
- O export de schemas dá a consumidores externos um contrato verificável sem
  depender do código Python.
