# Forge Ecosystem Integration — Cycle 08 (ds-0096)

Verificado nesta sessão (2026, commit pós-8a6a07b):

## 7.1 Capability Discovery

- `data-sentinel capabilities [--json]` — 13 capabilities versionadas
  (name + version + platforms), emitidas pelo registro real de
  analyzers. Nada é declarado que não exista em código.
- MCP `list_tools` expõe os 20+ tools `sentinel.*` com JSON Schema
  real por tool (gerado de `ToolDescriptor.input_schema`).

## 7.2 MCP — verificado

`pytest -k mcp` → 8 testes verdes cobrindo: tool discovery, invocação
round-trip via stdio, validação de input, erro em tool desconhecida
(`is_error`), enforcement de permissões e saída com evidência.

## 7.3 Doctor Interoperability

- `sentinel.doctor.import_bundle` — importa bundles `forge-contracts/1`.
- `DiagnosticReport → bundle` export (Cycle 04, ds-0046) — round-trip
  reimport provado.
- Nenhuma dependência obrigatória: `import_doctor_bundle` é lazy-import
  dentro do dispatcher do registry.

## 7.4 Spark Forge AWS — fluxo conceitual (documentado, não implementado)

```
Sentinel investiga → exporta evidências (bundle forge-contracts/1)
  → Spark Forge AWS consome evidências e auxilia a implementação
  → Sentinel re-analisa o resultado (snapshot/compare)
```

Nenhum código de outro repositório foi alterado. A integração é por
contrato de artefatos, não por chamada de API entre projetos.

## 7.5 O que NÃO está disponível (honesto)

- Nenhum comando `forge`/`sentinel` invoca outro binário
  automaticamente — integração é manual via exportação de artefatos.
- Forge Portal: sem plugin/conector dedicado neste ciclo.
