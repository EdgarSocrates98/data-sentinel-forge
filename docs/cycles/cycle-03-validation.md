# Cycle 03 — Validação

Executado no SHA da implementação (Linux, Python 3.12, uv):

| Verificação | Resultado |
|---|---|
| `uv run pytest -q` | **488 passed, 3 skipped** (~15.5s) |
| golden | 26/26 manifests |
| security cycle3 | 10 testes (injection, cyclic, oversized, KMS, policies) |
| benchmarks | `docs/evidence/benchmarks-cycle3.json` gerado |
| e2e A–F | 6 cenários |
| `uv run ruff check src tests` | clean |
| `uv run mypy src` | 90+ arquivos, 0 issues strict |
| `uv build` | wheel+sdist; YAMLs de regras confirmados no wheel |
| venv limpa | `load_packaged_rules()` → 10 regras fora do checkout |
| `data-sentinel doctor` | 10 analyzers, store ok, redação ok |

## Skips (esperados)

- 2× AWS real env-gated (`DATA_SENTINEL_AWS_TESTS`) — sem credenciais.
- 1× C02 real-AWS gated.

## AWS real — BLOCKED

`DATA_SENTINEL_AWS_TESTS=1` executa os testes gated: allowlist read-only
PASSA; chamada real falha `NoCredentialsError`. Sem `~/.aws` nem env vars —
homologação real registrada como **BLOCKED**; guia de execução manual em
`docs/guides/cross-account-diagnostics.md` §homologação.

## CI remota

Bloqueada por billing do repo privado (mesma situação do fechamento do
Cycle 02 — jobs não iniciam). Comandos equivalentes passam localmente.
