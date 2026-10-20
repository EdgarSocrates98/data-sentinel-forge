# Guia — Data Quality no Data Sentinel

## Filosofia
Determinístico, offline, evidence-first. Sentinel **não executa** engines
de qualidade (Deequ, GE) — ela **normaliza resultados exportados** e
avalia regressões/drift. Um resultado ausente nunca vira PASS.

## Contrato declarativo (§3.2)

```yaml
contract_version: "1.0"
dataset: analytics.customer_events
rules:
  - id: customer_id_not_null
    type: completeness
    column: customer_id
    expected: 1.0
    severity: high
  - id: minimum_volume
    type: row_count
    minimum: 100000
```

Validar:
```bash
data-sentinel quality validate --file contrato.yaml
data-sentinel quality validate --file contrato.yaml --json
```

Campos por regra: `id`, `type`, `column`/`columns`/`target`, `expected`,
`severity`, `tolerance`, e quaisquer extras (preservados em `parameters`).

## Importando resultados exportados

```bash
data-sentinel quality import --file pydeequ_metrics.json --adapter pydeequ
data-sentinel quality import --file ge_result.json --adapter great_expectations --json
data-sentinel quality import --file rows.json --adapter sql_results
data-sentinel quality import --file result.json        # auto-detect
```

Adapters declarados (`data_sentinel.quality.list_adapters()`): name,
version, input_format, available_fields, limitations, deps opcionais.

Regra de ouro: **falha/ausência do engine → UNKNOWN, nunca PASS.**

## Profiling & drift (extra `stats`)

```bash
pip install "data-sentinel[stats]"   # numpy + scipy
```

```python
from data_sentinel.quality.profile import profile_table, profile_column
from data_sentinel.quality.drift import detect_drift, drift_findings

prof = profile_column("amount", valores_observados)
res  = detect_drift("amount", baseline_samples, current_samples)
# res.level: none|low|medium|high|unknown; res.engine: scipy|heuristic
```

- scipy presente → KS two-sample / chi2 com p-value + confidence.
- scipy ausente → PSI / TV distance + limitation explícita.
- <5 amostras → UNKNOWN (nunca inventa).

## Versionamento de contrato
`check_version_compat(expected, found)`: MAJOR diverge → incompatível;
MINOR/PATCH novo → compatível com warning "campos desconhecidos
preservados mas não avaliados".

## Segurança
YAML via `safe_load` (tags `!!python/*` rejeitadas); contratos ≤1MB,
≤5k regras; parâmetros extras são dados inertes — nunca avaliados.
