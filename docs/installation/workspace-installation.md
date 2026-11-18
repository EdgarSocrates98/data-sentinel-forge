# Escopo workspace

```bash
data-sentinel install --scope workspace --root /caminho/ws --yes
```

Para monorepos/diretórios de trabalho compartilhados: aplica o mesmo
conjunto de assets no root do workspace. O state dir fica em
`<ws>/.data-sentinel/install`.

## Resolução do root (install-2.1)

- `--root` explícito é **autoritativo**: um marcador de workspace em um
  ancestral (`forge.workspace.{yaml,json}`, `.forge-workspace`, ou
  `pyproject.toml` com `[tool.forge.workspace]`/`[tool.uv.workspace]`)
  nunca substitui o caminho pedido — a caminhada só sobe a partir do
  cwd quando `--root` não é dado.
- Sem `--root`, o workspace scope resolve o marcador de workspace mais
  próximo acima do cwd; sem marcador, cai no root VCS (`.git`) e depois
  no próprio cwd.
- Membros são descobertos **com ou sem `.git`**: qualquer diretório com
  `forge.json`, `forge.agentic.json`, `pyproject.toml` ou `package.json`
  conta como projeto. A varredura nunca segue symlinks/junctions, pula
  diretórios ocultos e ignorados (`node_modules`, `.venv`, `dist`,
  `build`, caches…) e nunca desce dentro de um membro já descoberto.

## `--host none` e o context registry

`--host none` não escreve nenhum asset de host (nenhum `SKILL.md`), mas
`.forge/context/` **continua sendo escrito** — é o registro de
workspace compartilhado entre forges (manifest + `registry.json` +
`ROUTING.md` + blocos `forge:*` nos consumer docs), não um asset de
host. Isso é intencional e **mandatório**: o registry descreve a forge
instalada para os outros participantes do workspace e não há flag de
opt-out para escopos `project`/`workspace` — uma falha no registro
derruba o install (`status: failed`). O escopo `user` é a exceção por
desenho: `~/.forge/` é nível de conta e contexto de workspace nunca é
escrito lá.
