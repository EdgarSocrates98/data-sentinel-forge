# Integração com The Forge (opcional)

O Data Sentinel expõe um inventário de capacidades consumível por
orquestradores — sem exigir The Forge (ou qualquer componente do
ecossistema) em runtime.

## Descoberta

```bash
data-sentinel capabilities --descriptors
```

Emite uma lista JSON de `CapabilityDescriptor` (schema
`schemas/CapabilityDescriptor.schema.json`, interop 1.0.0) cobrindo:

- `sentinel.<analyzer>` — um por analyzer registrado (10 no baseline)
- `sentinel.import.doctor-bundle` — importação de bundles Doctor
- `sentinel.incident.graph` — grafo de evidência operacional

Cada descriptor declara `input_types`, `output_types`, `permissions` e
`limitations` — o orquestrador roteia pelo `capability_id` sem conhecer
implementação.

## Fluxo pretendido (The Forge)

1. Forge consulta `capabilities --descriptors` uma vez por instalação.
2. Para diagnóstico operacional, invoca `data-sentinel analyze|glue|spark|
   sql|lakehouse ... --json` e consome `DiagnosticReport` (schema 1.0.0).
3. Para findings de auditoria estática, prefere o bundle do Doctor via
   `import doctor-bundle` — o Sentinel os correlaciona sem promovê-los a
   evidência observada.

## Garantias de independência

- Nenhum comando requer pacotes do ecossistema instalados.
- A suíte de testes roda inteira sem Doctor/Forge/AWS (verificado no CI
  equivalente local: 500+ testes).
- Não há imports de `forge_*` em `src/`.
