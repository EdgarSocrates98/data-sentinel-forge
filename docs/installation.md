# Instalação

## Instalador portátil

A partir de um checkout, instale o CLI em uma venv user-scoped sem depender
do workspace depois da instalação:

```bash
./install.sh              # Linux/macOS/Git Bash
./install.sh --dry-run    # mostra o plano sem escrever
```

No PowerShell use `.\install.ps1`; `install.windows.sh` é a rota equivalente
para Git Bash. Os três wrappers executam `scripts/forge_bootstrap.py`: a
venv fica em `~/.forge/installs/data-sentinel-forge/.venv` (ou
`--install-dir`), o shim `data-sentinel` em `~/.local/bin/` e o
manifesto/receipt em `~/.forge/installations/`. Adicione `~/.local/bin`
ao `PATH` uma vez. Depois, `data-sentinel install` continua sendo o fluxo
agentic para skills, agents e integrações de host.

`scripts/install_portable.py` é o instalador portátil **legado** (rote
alternativa, ainda funcional e coberta por teste): instala em
`~/.forjas/data-sentinel-forge/` ou `FORGE_INSTALL_HOME` sem depender do
checkout depois da instalação. O caminho suportado hoje é
`install.sh`/`install.ps1` → `forge_bootstrap.py`; o legado fica como
fallback documentado para ambientes restritos.

## Verificado nesta sessão

| Verificação | Método | Resultado |
|---|---|---|
| Wheel limpa | `uv build` → `dist/data_sentinel_forge-*.whl` | OK |
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

`aws` (boto3), `api` (fastapi/uvicorn), `mcp`, `stats` (numpy/scipy),
`dev` — nomes exatos em `pyproject.toml`.

## Offline

O pacote core não faz chamadas de rede. Conectores AWS existem mas são
opt-in via extra `aws` + credenciais explícitas; sem credenciais, nada
é tentado (ver `docs/cycles/cycle-08-aws-homologation.md`).

## Atualização / desinstalação

`pip install -U .` (no checkout) ou `pip install -U "data-sentinel-forge @
git+https://github.com/EdgarSocrates98/data-sentinel-forge"` até a
publicação no PyPI; `pip uninstall data-sentinel-forge` para remover.
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

### Receipts honestos (cycle 16.1)

Todo documento `forge/InstallReceipt/v1` e `forge/InstallationHealth/v1`
emite um bloco `lifecycle` (`forge/InstallLifecycle/v1`) com o estado
derivado da evidência — `planned`, `blocked`, `failed`, `applied`,
`partially_applied`, `verified`, `unverified`, `ready`, `certified`.
`status: completed` significa apenas "o writer terminou"; a posição fina
é `lifecycle.state` (`verified` = writes + verificação `PASS`, `ready` =
verificado + saúde verde).

O receipt de install também carrega `counts` — contabilidade incremental
por ação (`created`/`updated`/`unchanged`/`adopted`/`skipped`,
`written`, `written_bytes`). Um reinstall sobre instalação idêntica
reporta `written: 0`/`written_bytes: 0` e não re-toca arquivos
byte-idênticos (só ledger/receipts de estado mudam).

Em `.mcp.json`, a chave gerenciada usa argv independente de PATH: o
`cli.shim` absoluto registrado pelo bootstrap, ou `python -m
data_sentinel mcp serve` (interpretador absoluto + módulo) — nunca um
nome bare que dependa do `PATH` do host. `install status|doctor`
reconhece install "docs-only" (ledger vazio + entrada em
`.forge/context/registry.json`) como `healthy` com
`context_registered: true`, nunca `unverified` falso.

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
