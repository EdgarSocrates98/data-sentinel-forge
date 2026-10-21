# Devin CLI

Layout: `.devin/skills/`, `.devin/agents/` + espelho `.agents/skills`,
`.agents/agents` (Devin lê os dois). Mirrors `.agents/` omitem `tools:`
(mapping não documentado) — a fronteira é o texto `## Não faz`.

```bash
data-sentinel install --host devin --yes
```

Skills com `subagent: true`/`agent:` só onde dispatchable está registrado.
