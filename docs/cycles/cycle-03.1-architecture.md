# Cycle 03.1 — Architecture

Novos componentes (todos aditivos):

```
src/data_sentinel/
├── core/contracts/interop.py      # forge-contracts/1 + envelope §3.1 (interop 1.0.0)
├── adapters/doctor/adapter.py     # detect→normalize→internal (import-only, offline)
├── diagnostics/
│   ├── incident.py                # EvidenceGraph + UnifiedExecutionContext
│   ├── timeline.py                # +EventKind, gaps, merge multi-fonte (estendido)
│   └── capabilities.py            # CapabilityDescriptor discovery
└── cli                            # + import doctor-bundle, capabilities --descriptors
```

## Fronteira de domínio (ADR 0012)

Divisão por TIPO DE EVIDÊNCIA, não por domínio:
- Doctor → auditoria estática (STATIC/CONFIG) de projeto/código.
- Sentinel → inteligência operacional (OBSERVED/DECLARED) de execução.
- Overlap de domínio é legítimo quando produz classes de evidência
  diferentes para perguntas diferentes.

## Interoperabilidade

- **Import-only** (grill gate): Doctor bundle → `ExternalDiagnosticBundle`
  → Findings internos com `provenance=declared`, nunca CONFIRMED.
- **Sem dependência cíclica**: zero imports `forge_*` no código-fonte.
- **Capability discovery**: `capabilities --descriptors` expõe 12
  descriptors consumíveis por orquestradores.

## Decisões-chave

1. Vocabulário `forge-contracts/1` adotado (não reinventado) — §3.3.
2. Findings importados = Finding interno + proveniência (grill gate #3).
3. Knowledge pack compartilhado: NÃO criado — fatos vs vereditos
   operacionais têm schemas divergentes (reuse-dedup.md).
4. Grafo de incidente: correlação exige vínculo justificável; causal
   separada de associação.
