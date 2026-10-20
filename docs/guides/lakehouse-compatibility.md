# Guia — Compatibilidade lakehouse

```bash
data-sentinel lakehouse compat --runtime glue-5.1 --operation merge \
    --access-mode fgac --table-format iceberg [--json]
```

Vereditos: SUPPORTED, SUPPORTED_WITH_CONSTRAINTS, UNSUPPORTED, UNKNOWN,
NOT_VERIFIED — **não verificado ≠ não suportado**.

## Matriz coberta (regras empacotadas)

| Runtime | Formato | Modo | Veredito |
|---|---|---|---|
| glue-4.0 | iceberg | * | WITH_CONSTRAINTS (v1/v2) |
| glue-4.0 | iceberg-v3 | * | UNSUPPORTED |
| glue-5.0 | iceberg | fgac | WITH_CONSTRAINTS |
| glue-5.1 | iceberg | * | SUPPORTED |
| glue-5.1 | iceberg | fgac | WITH_CONSTRAINTS |
| glue-5.1 | iceberg-v3 | * | NOT_VERIFIED |

Regras novas entram em `knowledge/rules/*.yaml` com fonte, versão, data,
owner, reviewer e histórico — validação automática bloqueia regra sem
proveniência. Empate de especificidade → UNKNOWN + conflito reportado
(revisão humana registrada).
