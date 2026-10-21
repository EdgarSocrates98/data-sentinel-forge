# Componentes opcionais

`skills`, `agents`, `mcp`, `tui`, `graph-studio`.

```bash
data-sentinel install --components skills --yes      # só skills
data-sentinel install --components skills,mcp --yes  # skills + MCP
```

| Componente | Efeito |
|---|---|
| `skills` | 5 skills `data-sentinel-*` nos dirs do host |
| `agents` | 3 manifests de agente nos dirs do host |
| `mcp` | entrada `data-sentinel` em `.mcp.json` |
| `tui` | reservado — Control Center/TUI |
| `graph-studio` | reservado — graph studio |
