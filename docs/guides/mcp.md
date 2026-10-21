# MCP Server — Data Sentinel

## Executar

```bash
pip install ".[mcp]"   # no checkout
data-sentinel mcp serve
# ou: python -m data_sentinel.mcp_server
```

Transporte: **stdio local apenas**. Sem transporte remoto neste ciclo
(exige auth/abuse-protection não implementadas).

## Ferramentas expostas

Todas as `sentinel.*` do Tool Registry — mesmos serviços da CLI,
sem regras duplicadas. Parâmetros comuns: `file`, `adapter`, `target`,
`baseline_file`, `current_file`.

## Compatibilidade por host

| Host | Suporte | Notas |
|---|---|---|
| Claude Code | Sim | `claude mcp add --transport stdio data-sentinel -- data-sentinel mcp serve` |
| Cursor | Sim | settings MCP: command=`data-sentinel`, args=`mcp serve` |
| Codex | Provável | MCP stdio genérico; fluxo de instalação varia por versão |
| Devin | Provável | quando host suportar MCP stdio |

Requisitos: pacote instalado + extra `mcp`. Sem Forge/Doctor/AWS para
ferramentas offline — instalação independente validada por teste real
de subprocesso (`tests/integration/test_mcp_stdio.py`).

## Limitações honestas
- Sem recursos/prompts MCP — apenas tools neste ciclo.
- Erros de tool são retornados como dados (`{"error": ...}`), não crash.
- Sem autenticação (stdio local; credenciais nunca passam pelo protocolo).
