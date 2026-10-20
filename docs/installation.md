# Instalação — Cycle 08 (ds-0093)

## Verificado nesta sessão

| Verificação | Método | Resultado |
|---|---|---|
| Wheel limpa | `uv build` → `dist/data_sentinel-0.1.0-py3-none-any.whl` | OK |
| Instalação em venv limpa | `uv venv --seed /tmp/ds8-venv` + `uv pip install dist/*.whl` | OK |
| Import | `python -c "import data_sentinel"` | OK |
| CLI | `data-sentinel --help`, `capabilities`, `investigate run` | OK — 2 findings reais em fixture Spark |
| Offline | toda a verificação acima sem rede (deps já em cache uv) | OK |

## Plataformas suportadas

- Python ≥ 3.11 (testado em 3.12).
- Linux (desenvolvimento/verificação); macOS/Windows por Python puro —
  sem binários nativos na wheel core.
- Node 22 + npm apenas para o frontend Angular (opcional, dev-only).

## Extras

aws (boto3), api (fastapi/uvicorn), mcp, stats (numpy/scipy), dev — nomes exatos em pyproject.toml.
`api` (fastapi/uvicorn), `mcp`, `stats` (numpy/scipy), `dev`.

## Offline

O pacote core não faz chamadas de rede. Conectores AWS existem mas são
opt-in via extra `aws` + credenciais explícitas; sem credenciais, nada
é tentado (ver `docs/cycles/cycle-08-aws-homologation.md`).

## Atualização / desinstalação

`pip install -U data-sentinel` / `pip uninstall data-sentinel`.
Dados locais em `~/.data-sentinel/` (SQLite + token) sobrevivem à
desinstalação — remover manualmente se desejado.
