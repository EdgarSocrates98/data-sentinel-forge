# Instalação

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

`pip install -U .` (no checkout) ou `pip install -U "data-sentinel @
git+https://github.com/EdgarSocrates98/data-sentinel-forge"` até a
publicação no PyPI; `pip uninstall data-sentinel` para remover.
Dados locais em `~/.data-sentinel/` (SQLite + token) sobrevivem à
desinstalação — remover manualmente se desejado.

## Instalação agentic (Cycle 08.2)

`data-sentinel install` instala skills/agents/mcp nos hosts suportados
(Claude, Devin, Codex, Copilot; Cursor declarado sem adapter de catálogo).
Todos os writes passam pelo ledger do installkit vendored — arquivos do
usuário nunca são sobrescritos; conflitos geram backup + receipt.

| Comando | Função |
|---|---|
| `data-sentinel install` | interativo (TTY) ou `--yes --profile` |
| `data-sentinel install env` | descoberta de ambiente — Python, tools, hosts detectados, registry `~/.forge` |
| `data-sentinel install status` | instalações, receipts, arquivos gerenciados, drift |
| `data-sentinel install doctor` | runtime, config, handshake MCP, assets — findings acionáveis |
| `data-sentinel install repair` | restaura managed files corrompidos; recusa arquivos estrangeiros |
| `data-sentinel install uninstall` | remove só o que o ledger possui (`--purge` remove o state dir) |
| `data-sentinel install mcp-verify` | handshake MCP real (initialize + tools/list) |

### Variáveis de ambiente

O pacote não lê `.env` — configuração é via flags do CLI e três
variáveis documentadas (`install env` reporta `set`/`unset`, nunca valores):

| Variável | Efeito |
|---|---|
| `DATA_SENTINEL_DB` | path do SQLite de investigações |
| `DATA_SENTINEL_MCP_ROOTS` | roots extras permitidos no servidor MCP (`:`-separados) |
| `DATA_SENTINEL_TOKEN` | bearer token do `data-sentinel serve` |

### Ambientes corporativos

O core não faz network I/O. `uv`/`pip` honram `HTTPS_PROXY` e
`PIP_INDEX_URL` para instalação por trás de proxy/index interno.
Assets (skills/agents/manifests) viajam dentro da wheel — nenhum download
adicional é necessário em runtime.
