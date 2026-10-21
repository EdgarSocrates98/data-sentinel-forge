# Copilot

Layout: `.github/skills/`, `.github/agents/<nome>.agent.md`.

```bash
data-sentinel install --host copilot --yes
```

## Cursor (limitação declarada)

Cursor é host declarado mas **sem adapter de catálogo** — não recebe
skills/agents. Apenas marker/MCP compartilhados se aplicam. Instalar
com `--host cursor` não gera `SKILL.md` — comportamento intencional.
