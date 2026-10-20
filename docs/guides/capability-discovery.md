# Capability Discovery

## Comando

```bash
data-sentinel capabilities            # manifests humanos
data-sentinel capabilities --json     # manifests JSON (schema 1.0.0)
data-sentinel capabilities --descriptors  # CapabilityDescriptor (interop 1.0.0)
```

## O que `--descriptors` emite

Um array JSON ordenado deterministicamente de `CapabilityDescriptor`
(schema: `schemas/CapabilityDescriptor.schema.json`):

- `sentinel.<analyzer>` — um por analyzer registrado (10 no baseline)
- `sentinel.import.doctor-bundle` — superfície de importação
- `sentinel.incident.graph` — grafo de evidência operacional

Cada descriptor carrega `input_types`, `output_types`, `permissions`
necessárias e `limitations` honestas — um orquestrador (ex.: The Forge)
pode rotear por `capability_id` sem conhecer a implementação.

## Garantias

- Nada é obrigatório em runtime: o inventário é autodescrição, não
  registro num servidor. Sem LLM, sem AWS, sem ecossistema.
- `permissions` declara o que cada superfície precisa (ex.:
  `filesystem:read` para import); ausência = sem exigência extra.
