# Agentic layer (Cycle 05)

Camada opcional e **determinística-primeiro** sobre os analyzers.

## Componentes

| Componente | Módulo | O que faz |
|---|---|---|
| Contratos | `core/contracts/agent.py` | AgentDescriptor/Task/Execution/State/Plan/Budget/Tool*/Hypothesis/Report |
| Runtime | `agents/runtime.py` | máquina de estados, budgets, relógio injetável |
| Providers | `agents/providers.py` | StubProvider (offline) + HTTP local (localhost-only) |
| Especialistas | `agents/specialists.py` | 12 agentes, roteamento por keyword |
| Tools | `tools/registry.py` | 21 tools sobre os analyzers existentes |
| MCP | `mcp_server.py` | servidor stdio (SDK `mcp`, extra opcional) |
| Contexto | `context/` | camadas ordenadas, budget de tokens, cache LRU |
| RAG | `rag/` | TF-IDF lexical com proveniência; memória JSONL |
| Reasoning | `reasoning/` | RCA por cluster + validador independente |
| Guardrails | `agents/guardrails.py` | 6 classes de permissão, redação de segredos, anti-injeção |
| Orquestração | `agents/investigator.py` | pipeline: route→tools→validate→RCA→report |

## Uso

```bash
data-sentinel agents                       # lista especialistas
data-sentinel tools                        # lista tools
data-sentinel investigate run -p "sql lenta" \
  -f sentinel.sql.analyze:query.sql --json
data-sentinel mcp serve                    # servidor MCP stdio
```

## Limitações honestas

- Roteamento é por keyword — não semântico. LLM opcional nunca é exigido.
- RAG é lexical (TF-IDF); sem embeddings nem rerank neural.
- MCP cobre stdio local; transporte remoto fora de escopo.
- `investigate` exige pares `tool:path` explícitos — não adivinha tool
  a partir do arquivo.
- Especialistas sem `allowed_tools` (coordinator, RCA, validator,
  report) operam sobre os findings já coletados.
