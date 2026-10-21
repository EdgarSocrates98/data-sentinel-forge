# Escopo project (padrão)

```bash
cd meu-projeto
data-sentinel install --scope project --yes --host claude
```

Escreve dentro do diretório do projeto:

- `.claude/skills/`, `.claude/agents/` (host claude)
- `.devin/`, `.agents/` (devin), `.agents/` + `.codex/agents` (codex),
  `.github/` (copilot)
- `.mcp.json` (merged — servidores estrangeiros preservados)
- `AGENTS.md`/`CLAUDE.md` — bloco entre marcadores `data-sentinel-forge:managed`
- `.data-sentinel/install/` — state dir (ledger, journal, receipts)

Nada fora do root é tocado.
