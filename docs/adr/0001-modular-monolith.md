# ADR 0001 — Modular monolith

**Status:** accepted
**Data:** Cycle 01 (ds-0001..ds-0008)

## Contexto

O plano mestre exige um produto instalável e utilizável offline já no Cycle 01,
com CLI, API e MCP como interfaces de primeira classe nos ciclos seguintes.

## Decisão

O Data Sentinel é um monólito modular em um único pacote Python
(`data_sentinel`), com fronteiras internas por domínio: `core/` (contracts,
configuration, security, exceptions), `analyzers/`, `persistence/`, `cli/` e
pacotes placeholder (`api/`, `mcp/`, `intelligence/`, `connectors/`).

## Consequências

- Interfaces futuras (API/MCP) consomem os mesmos contratos e analyzers sem
  duplicação ou rede interna.
- Comunicação entre módulos ocorre exclusivamente via contratos públicos de
  `core/contracts` — implementação interna não vaza para consumidores.
- A extração de serviços separados, se um dia necessária, fica barata porque as
  fronteiras já existem.
