# Configuração

`load_config()` (em `core/configuration`) resolve a configuração efetiva com
precedência documentada — da maior para a menor:

| # | Fonte | Como é aplicada |
|---|---|---|
| 1 | Argumentos CLI | passados por `load_config(cli_overrides=...)` na camada de comando (ex.: `--profile`) |
| 2 | Variáveis `DATA_SENTINEL_*` | mapeadas para campos do modelo (`DATA_SENTINEL_PROFILE`, `DATA_SENTINEL_STORE_PATH`, …) |
| 3 | `data-sentinel.toml` do projeto | procurado do cwd **subindo** até a raiz |
| 4 | `~/.config/data-sentinel/config.toml` | respeita `XDG_CONFIG_HOME` |
| 5 | Defaults seguros | embutidos no modelo Pydantic |

Arquivos ausentes são tolerados; TOML inválido gera `ConfigurationError` com
código, mensagem PT-BR e a fonte que falhou. `config show` lista cada fonte
com estado `aplicada`/`encontrada`/`ausente`.

## Campos

| Campo | Tipo | Default | Nota |
|---|---|---|---|
| `profile` | `economy`/`balanced`/`deep`/`offline` | `balanced` | perfil de análise |
| `log_level` | `DEBUG`…`CRITICAL` | `INFO` | — |
| `output_format` | `text`/`json` | `text` | formato padrão de saída |
| `max_file_bytes` | int > 0 | pelo perfil | limite de leitura de artefato |
| `max_evidence_excerpt_chars` | int > 0 | pelo perfil | truncagem de evidência |
| `redact_secrets` | bool | `true` | redação ativa por padrão |
| `store_path` | str | `~/.local/share/data-sentinel` | diretório do SQLite (0700) |
| `allowed_roots` | list[str] | `[]` | raízes extras aceitas pelo path guard |

## Perfis

| Perfil | `max_file_bytes` | `max_evidence_excerpt_chars` | `allow_network` |
|---|---|---|---|
| economy | 10 MB | 2.000 | true |
| balanced | 50 MB | 8.000 | true |
| deep | 200 MB | 32.000 | true |
| offline | 50 MB | 8.000 | **false** |

`token_budget` e `tool_call_budget` existem no modelo como placeholders do
Cycle 05 (orçamentos de LLM) — sem efeito hoje.

## Segredos

Representações (`repr`, dumps, `config show`, modo `"redacted"`) passam por
`to_redacted_dict()`: chaves que parecem segredo viram `«redacted:…»` e
nunca aparecem em texto puro.

## Exemplo `data-sentinel.toml`

```toml
profile = "offline"
max_file_bytes = 10485760
allowed_roots = ["/var/log/jobs"]
```
