# Cycle 02 — Validação

Evidência de homologação executada nesta sessão. Log completo:
`factory/runs/ds-0019.verification.log`. Nada aqui é afirmado sem comando
executado.

## Homologação executada

| Passo | Comando | Resultado |
|---|---|---|
| Instalação limpa | `uv venv --seed` + `uv pip install .` + `data-sentinel version` | `data-sentinel 0.1.0` — wheel instala e roda |
| Core sem boto3 | `python -c "import boto3"` na venv limpa | `ModuleNotFoundError` — boto3 **não** é dependência core |
| Offline run | `analyze --file fixtures/logs/glue_oom.log` na venv limpa | `HIGH/CONFIRMED` OOM com evidência — zero rede |
| Recusa AWS limpa | `glue runs` sem boto3 | `aws.boto3_ausente` com instrução de instalação (exit 1) |
| Suite completa | `uv run pytest -q` | **360 passed, 1 skipped** (~5-6s) |
| Mocked AWS | Stubber dentro da suite | allowlist/paginação/erros IAM cobertos — **validado com mocks, não AWS real** |
| Schemas | `uv run pytest tests/contract` | 9 testes — schema↔modelo + round-trip JSON |
| Lint | `uv run ruff check src tests` | All checks passed |
| Type | `uv run mypy src` | 75 arquivos, 0 issues (strict) |
| Cobertura | `pytest --cov` | **88%** (2723 statements) |
| Docs spot-check | 3 comandos de guides/examples verbatim | todos produzem relatório real |

## Suites (contagem real)

| Suite | Testes | O que cobre |
|---|---|---|
| `tests/unit` | 228 | analyzers, parser de plano, joins, config advisor, correlação, timeline, orquestrador, renderers, conectores Stubber |
| `tests/integration` | 34 | CLI fim-a-fim (grupos novos + legado), persistência, markdown |
| `tests/contract` | 9 | JSON Schemas ↔ contratos Pydantic |
| `tests/security` | 55 | traversal, oversize, redação, payloads hostis em plano/SQL/stats, allowlist AWS, quadratic regex |
| `tests/golden` | 20 | cenários com findings esperados/proibidos + evidência + limitações |
| `tests/e2e` | 6 | E2E A–E do §11 + AWS real env-gated (skip) |
| `tests/benchmarks` | 9 | tempos reais + metadados → `docs/evidence/benchmarks.json` |

## Benchmarks (medidos, não estimados)

`docs/evidence/benchmarks.json` — Linux x86_64, CPython 3.12.3:

- parse de plano: 8 linhas ≈ 0.1ms; 4000 linhas ≈ 58ms (~linear)
- parse SQL (sqlglot): ~0.36ms por query média
- análise de log: 8000 linhas ≈ 191ms
- análise de plano 500×: ~60ms; relatório markdown: ~10µs
- memória: análise de log 1000× → pico ~1.0MB sobre input 314KB
- chamadas AWS: 150 runs = 3 chamadas paginadas (cap respeitado)

## Bug encontrado pela própria suíte de segurança

`test_oversized_lines_capped` expôs `_STAT_KV` quadrático (backtracking
O(n²) em linhas >8KB repetitivas — ~330s). Fix: valor limitado a
`{1,200}` chars + scan limitado a prefixo de 8KB
(`analyzers/spark/plans/parser.py`). A suíte caiu de 337s para ~6s.

## Restrição AWS — declarada conforme Grill Gate

Todo o código AWS (Glue + CloudWatch) foi **validado com
mocks/Stubber, não com AWS real**. O teste E2E opcional contra AWS real
fica gated por `DATA_SENTINEL_AWS_TESTS=1` (skipped por padrão) —
projetado para credenciais não-prod.
