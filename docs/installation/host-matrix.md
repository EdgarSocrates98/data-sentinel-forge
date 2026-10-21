# Host capability matrix (ds-0111)

Which component kinds each host adapter verifiably supports. Layouts are
audited against the canonical installkit `HOST_DIRS` contract and the
sibling-forge conventions (`sparkforge_aws/install/hosts.py`,
`integrate/hosts.py`). Anything unverified is **not claimed** — a host
with no homologated surface renders nothing and the reason is recorded
in `hosts.UNSUPPORTED_HOSTS`.

| Host    | Skills dirs (project)              | Agents dirs (project)             | Agent format | MCP | Notes |
|---------|------------------------------------|-----------------------------------|--------------|-----|-------|
| claude  | `.claude/skills/`                  | `.claude/agents/`                 | Markdown (byte-identical) | yes | canonical kit mapping |
| devin   | `.devin/skills/` + `.agents/skills/` | `.devin/agents/` + `.agents/agents/` | Markdown (`tools:` dropped) | yes | Devin reads `.agents/` natively; dispatchable skills get `subagent: true` + `agent:` |
| codex   | `.agents/skills/`                  | `.codex/agents/`                  | TOML         | yes | TOML = `name`/`description`/`developer_instructions` |
| copilot | `.github/skills/`                  | `.github/agents/`                 | `*.agent.md` | yes | user scope falls back to `~/.agents/` + `~/.copilot/agents` |
| cursor  | —                                  | —                                 | —            | yes | **no homologated surface**: install delivers the `AGENTS.md` managed marker (Cursor reads it natively) + `.mcp.json` only |

## User scope

`~/.claude/`, `~/.agents/` shared mirror, `~/.codex/`, `~/.copilot/` and
`~/.config/devin` (`%APPDATA%\devin` on Windows).

## Rules

- Dispatch decisions are declared, not silent: `DISPATCHABLE_SKILLS` /
  `NON_DISPATCHABLE_SKILLS` in `installation/hosts.py` carry the reason
  per skill. A skill without a registered decision fails the render.
- The `sentinel-investigator` profile is an orchestrator — never the
  `agent:` target of a dispatchable skill (subagents can't spawn
  subagents).
- All writes go through the installkit ownership ledger — pre-existing
  user files are adopted or refused, never silently overwritten.
- `forge.json` / `forge.agentic.json` are discovery manifests at the
  repo root, not project assets — they are never mirrored into hosts.
