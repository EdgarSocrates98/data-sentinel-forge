# Codex CLI

Layout: `.agents/skills/` + `.codex/agents/*.toml` (agents só no
`.codex/`; `.agents/` recebe apenas skills).
Agents Codex são TOML (`name`, `description`, `developer_instructions`).

```bash
data-sentinel install --host codex --yes
```

**Limitação conhecida:** Codex não consome `.mcp.json` de projeto — o
installkit reporta isso como `NOT_APPLICABLE` no health doc, não como
instalado. MCP para Codex exige configuração manual no `~/.codex/`.
