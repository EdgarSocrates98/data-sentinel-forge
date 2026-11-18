# MCP — servidor data-sentinel

O install escreve `data-sentinel` em `.mcp.json` com comando resolvido
para o path absoluto do executável (fallback: nome bare).

```json
{"mcpServers": {"data-sentinel": {"command": "/abs/data-sentinel",
"args": ["mcp", "serve"]}}}
```

- Merge preserva servidores estrangeiros (chaves managed namespaced).
- Handshake real verificado: `data-sentinel install mcp-verify`
  (initialize + tools/list — 20 tools). Exit code honesto: `0` só com o
  handshake verificado (`healthy`); `FAIL`, `BLOCKED` (CLI não
  resolvível no PATH) e `NOT_APPLICABLE` saem `1` — não-verificável
  nunca é sucesso.
- Sem extra `mcp` instalado, doctor reporta `UNVERIFIED` — honesto.
- Roots: cwd do server + `DATA_SENTINEL_MCP_ROOTS` (`:`-separados).
