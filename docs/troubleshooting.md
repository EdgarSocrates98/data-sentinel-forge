# Troubleshooting

Erros aparecem em **stderr** como `erro: <mensagem> [<código>]` e saem com
código não-zero. `--verbose` adiciona detalhes técnicos.

## `caminho fora das raízes permitidas` (exit 1)

O path guard rejeitou a entrada. Causas:

- `..` no caminho resolvendo fora do cwd/`allowed_roots`.
- Path absoluto fora das raízes — adicione a raiz em `data-sentinel.toml`:
  ```toml
  allowed_roots = ["/var/log/jobs"]
  ```
- Symlink apontando para fora das raízes.

## `arquivo não encontrado` / `não é um arquivo regular` (exit 1)

Confira o caminho; o guard rejeita diretórios e inexistentes.

## `arquivo excede o limite` (exit 1)

O arquivo passou de `max_file_bytes` do perfil. Aumente no TOML ou use um
perfil maior (`--profile deep` = 200 MB).

## `conteúdo binário` (exit 1)

A entrada parece binária (NUL detectado). Converta para texto antes de
analisar — o produto não faz OCR nem decodifica formatos binários.

## `relatório não encontrado` (exit 1)

`report --input` aceita `report_id` persistido ou caminho de JSON exportado.
Para um id, confirme que o `analyze` rodou **sem** `--no-persist` e que o
`store_path` é o mesmo (veja `config show`).

## `arquivo de configuração inválido` (exit 1)

TOML quebrado em `data-sentinel.toml` ou `config.toml`. O erro traz caminho e
camada. `config show` mostra quais fontes foram encontradas.

## `doctor` FAIL em `store gravável`

Sem permissão para criar `store_path` (default
`~/.local/share/data-sentinel`). Ajuste `store_path` na config ou corrija
permissões.

## Nada acontece / saída vazia

- `analyze` sem `--file`/`--sql` → exit 2 com mensagem de uso.
- Achado `UNKNOWN` não é bug: o log não casa padrões conhecidos — a limitação
  no relatório diz quais artefatos ajudariam.
