# Cycle 05 — Relatório final

**Decisão: `APPROVED WITH RESTRICTIONS`**

## O que entrou

Camada agêntica completa sobre a base determinística dos ciclos 01–04:
contratos, runtime com budgets e estados, providers (stub + HTTP local),
16 tools, 12 especialistas, MCP stdio (SDK oficial 2.x), context
engineering com token budget e evidência preservada, RAG lexical,
memória de investigação, RCA, validador independente, guardrails de 6
classes, anti-injeção, redação de segredos, CLI `investigate/agents/
tools/mcp`, evals, E2E A–J, benchmarks.

## Verificação

- 672 testes, 3 skipped (env-gated); ruff+mypy strict limpos.
- MCP stdio round-trip real via `uv run python -m data_sentinel.mcp_server`
  (unknown tool → `is_error`, nunca exceção falsa).
- Benchmarks: `docs/evidence/benchmarks-cycle5.json`.
- Evals: `tests/evals/` — routing accuracy ≥80% gate real.

## Restrições honestas

- **LLM opcional**: StubProvider e HTTP local-only; nenhuma key paga
  testada (não há).
- **MCP SDK 2.x** em vez do ≥1.9 previsto — API diferente (`MCPServer`,
  `is_error`, sem FastMCP); código adaptado e pin `mcp>=1.9` mantido.
- **CI remota bloqueada por billing** (repo privado, pagamento falho) —
  equivalência local comprovada, mesmos comandos do `ci.yml`.
- Roteamento determinístico por keyword; RAG sem embeddings; sem
  delegação multi-hop entre especialistas — backlog C06.
- Nenhuma operação cloud-write/destrutiva adicionada (proibidas por
  `check_tool_permission`).
