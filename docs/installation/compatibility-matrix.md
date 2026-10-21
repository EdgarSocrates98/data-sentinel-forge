# Matriz de compatibilidade

| Host | skills | agents | mcp (`.mcp.json`) | marker |
|---|---|---|---|---|
| Claude | ✅ `.claude/skills` | ✅ `.claude/agents` | ✅ project | ✅ CLAUDE.md/AGENTS.md |
| Devin | ✅ `.devin/skills` + `.agents/` | ✅ `.devin/agents` + `.agents/` | ✅ project | ✅ |
| Codex | ✅ `.agents/skills` | ✅ TOML `.agents/`+`.codex/` | N-A project (não consome) | ✅ |
| Copilot | ✅ `.github/skills` | ✅ `.github/agents/*.agent.md` | ✅ project | ✅ |
| Cursor | ❌ sem adapter | ❌ sem adapter | shared | shared |

| Scope | Linux | macOS | Windows |
|---|---|---|---|
| project | ✅ | ✅ | ✅ |
| workspace | ✅ | ✅ | ✅ |
| user | ✅ | ✅ | ✅ |

Cross-platform homologado na matrix CI (ubuntu/macos/windows ×
3.11/3.12). PyPI: não publicado — instalação por wheel ou source.
