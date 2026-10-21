# Instalação standalone

O Sentinel funciona standalone — sem The Forge, sem forge-cli, sem AWS,
sem LLM. A distribuição `data-sentinel` (checkout ou git+https — PyPI
ainda não publicado) entrega o CLI completo:

```bash
data-sentinel capabilities     # inventário de tools
data-sentinel analyze --file log.txt
data-sentinel mcp serve        # servidor MCP stdio
```

A instalação agentic (`data-sentinel install`) é uma camada opcional
que publica skills/agents/MCP nos hosts. O core não depende dela.
