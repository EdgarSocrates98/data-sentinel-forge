# Escopo user

```bash
data-sentinel install --scope user --yes --host claude
```

Escreve nos diretórios home do host (`~/.claude/skills`, `~/.devin/`,
`~/.codex/`, `~/.config/` conforme o host) — skills/agents ficam
disponíveis em todos os projetos. O state dir vai para o home.

Use `--root` para apontar um home alternativo em testes.
