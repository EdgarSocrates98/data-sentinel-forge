# Segurança

Postura: **read-only por padrão, offline por padrão, evidência sanitizada por
padrão**.

## Path guard (`core/security/paths.py`)

`safe_resolve(path, allowed_roots)`:

- Rejeita escapes via `..` (o caminho resolvido deve ficar sob uma raiz).
- Rejeita symlinks que resolvam para fora das raízes.
- Rejeita caminhos inexistentes e não-arquivos.
- Paths absolutos só passam se a raiz do próprio path foi explicitamente
  permitida.

Na CLI, as raízes permitidas são `cwd + allowed_roots` da config — então
`analyze --file ../../etc/hostname` falha com erro amigável (exit 1), mesmo
sendo um caminho legítimo do SO.

## Leitura de entrada

`read_input_file()` aplica `max_file_bytes` do perfil e rejeita conteúdo
binário (NUL detection) com erro útil — nada de crash em lixo binário.

## Redação de segredos (`core/security/redact.py`)

`sanitize_evidence_excerpt()` é o **único ponto de entrada** de evidência para
analyzers e store — cobre:

- AWS access keys (`AKIA`/`ASIA…`) e secret keys em contexto
- Bearer tokens e headers `Authorization:` (Basic/Bearer)
- `token=`, `password=`, `secret=`, `api_key=`, `aws_secret_access_key=`
- Blocos de private key (`-----BEGIN … PRIVATE KEY-----`)
- Connection strings com credenciais embutidas
- Tokens no formato GitHub/Slack (`ghp_`, `xox[abprs]-`)

Substituições usam marcadores `«redacted:tipo»` — e os padrões foram escritos
para não re-casarem nos próprios marcadores.

## Sanitização (`core/security/sanitize.py`)

`sanitize_log_text()` remove ANSI/control chars (preserva `\n`/`\t`),
normaliza erros de decode e trunca com marcador explícito — a truncagem nunca
deixa fragmento de segredo no corte (verificado em teste).

## Persistência

- Store SQLite: dir criado `0700` (POSIX), journal WAL.
- Evidências são **re-sanitizadas na escrita** — defesa em profundidade caso
  um analyzer futuro produza excerpt cru.
- Somente excerpt sanitizado + hash sha256 persistem — nunca conteúdo raw.

## Garantias estruturais

- Nenhum `subprocess`/`os.system`/`eval`/`exec` em `src/` — teste de
  segurança varre a árvore.
- Nenhuma chamada de rede no núcleo; perfil `offline` declara
  `allow_network=false`.
- Erros de domínio expõem `code` + `message` PT-BR; `--verbose` é opt-in para
  detalhes técnicos.

## Limites conhecidos (honestos)

- A redação é regex-driven: formatos de segredo fora da biblioteca podem
  escapar — reporte em SECURITY.md.
- O path guard protege leitura de *entrada*; `--output` grava onde o usuário
  mandar (é uma escrita explícita do próprio usuário).
