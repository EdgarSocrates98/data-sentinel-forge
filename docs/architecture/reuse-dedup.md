# Reuse & Deduplication — Doctor × Sentinel (ds-0036)

Base: auditoria de código (`docs/audits/doctor-sentinel-audit.md`) +
inspeção direta dos knowledge packs dos dois produtos.

## Inventário de sobreposição por domínio

| Domínio | Doctor Data | Sentinel | Duplicação? | Estratégia |
|---|---|---|---|---|
| Versões Glue (EOL, spark/python por versão) | `knowledge/glue/versions.json` (schema_version 2, pack_version 2026.1, fontes AWS, cobre 0.9→6.0) | regras YAML glue-runtime-iceberg (4.0/5.0/5.1) | Semântica parcial — mesmo domínio, pergunta diferente | **B** compartilhar contrato |
| Iceberg compat (runtime×formato×feature) | `knowledge/iceberg/{spec,versions,compatibility}.json` — fatos estáticos de spec | `knowledge/compat.py` engine + regras — veredito operacional | Semântica parcial | **B** + consumo via bundle (R2) |
| FGAC/FTA Lake Formation | `knowledge/lakeformation/{permissions,hybrid,cross-account,errors}.json` + checks LF000-18 | `glue-fgac.yaml` + resolver + analyzer | Justificável — estático vs operacional | **A** manter separado |
| IAM S3/KMS | checks TF0xx (IaC scan de policies em Terraform) | avaliador offline de policy JSON no contexto de incidente | Complementar real | **A** |
| MERGE/APPEND | padrões textuais em model files (ICE/DELTA) | analyzer sqlglot AST dedicado | Complementar | **A** |
| Schema evolution | `core/schema.py` diff de schemas de projeto | analyzer de evolução em metadata Iceberg | Complementar | **A** |
| Small files | PARQ000-42 (file-size em scan de projeto) + ICE maintenance | heurística de snapshot/metadata (conditional) | Complementar | **A** |
| Spark skew/shuffle | SPARK001-11 checks + labs | plan analyzer + join intelligence em runtime | Complementar | **A** |
| Capability matrices | `capabilities/*` packs por plataforma | `CapabilityManifest` + SupportStatus + compat | Semântica forte | **B** compartilhar contrato (já via descriptors) |
| Findings/evidência | `forge-contracts/1` Finding/Evidence | `Finding`/`Evidence` internos | Resolvido por adapter | **C** adaptador (ds-0033 feito) |

## Duplicações semânticas reais detectadas

1. **Versões de runtime como fatos** — o mesmo fato ("Glue 4.0 usa Spark
   3.3/Python 3.10") existe nos dois lados com schemas diferentes.
   Doctor: JSON pack versionado com `verified_at` + `sources`.
   Sentinel: embutido no texto/constraint das regras YAML.
   → Risco real de divergência futura. Mitigação por **B**: o Doctor pack
   é mais rico e versionado; Sentinel pode consumi-lo via bundle/capability
   quando disponível (R2 abaixo), mantendo as próprias regras como fonte
   autoritativa local até lá — porque:
2. **Vereditos operacionais** — as regras YAML do Sentinel respondem
   "runtime X + formato Y + operação Z + modo de acesso W ⇒ suportado?".
   Os packs do Doctor registram fatos ("Iceberg 1.5 exige spec X"), não
   vereditos por operação. Semânticas diferentes → **A** justificado.

## Decisão sobre Knowledge Pack compartilhado (§6.3)

**NÃO criar pacote/repositório compartilhado novo** — justificativa:

- Os schemas divergem por necessidade real: Doctor pack = fatos
  versionados por fonte externa; Sentinel rules = vereditos multi-
  dimensionais (runtime×formato×op×access-mode) com precedência e
  resolução de conflito. Fundir exigiria um schema supra que nenhum lado
  precisa hoje.
- O contrato de interop (forge-contracts/1, já adotado) já transporta o
  conhecimento necessário como *capabilities/findings* — sem acoplamento
  de pacote.
- Critério do prompt: "não criar pacote compartilhado sem demonstrar
  benefício" — o benefício medido seria eliminar ~40 linhas de fatos
  sobre versões; custo = schema novo + lifecycle compartilhado.
  Não compensa neste ciclo. **Reavaliar no Cycle 04** se as regras de
  versão crescerem.

## Migration safety (§6.4) — checklist para realocações futuras

Antes de qualquer remoção/substituição:
1. Comparar inputs/outputs/findings lado a lado.
2. Rodar os 26 golden fixtures + E2E A–F.
3. Verificar falsos positivos/negativos contra corpus real.
4. Criar adapter/alias preservando CLI e schemas públicos.
5. Documentar em ADR + entrada no changelog.

**Nada foi removido nesta spec** — este documento é o plano.
