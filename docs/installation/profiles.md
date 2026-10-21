# Profiles de instalação

| Profile | Conteúdo |
|---|---|
| `minimal` | marker + MCP; sem skills/agents |
| `recommended` | marker + MCP + skills + agents (padrão) |
| `full` | tudo do recommended + componentes opcionais |

```bash
data-sentinel install --profile full --yes
```

O profile só controla *que tipos* de asset são planejados — os writes
sempre passam pelo ledger. `--components skills,agents` faz override
fino. `gateway` (`--gateway economy|balanced|deep`) é advisory —
registrado no receipt, nunca altera limites de segurança.
