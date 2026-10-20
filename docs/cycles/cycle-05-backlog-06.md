# Cycle 06 backlog (saída do Cycle 05)

- Roteamento semântico (embeddings locais ou LLM opcional por perfil).
- RAG com embeddings + rerank; GraphRAG sobre grafo de linhagem real.
- Delegação real entre especialistas (hoje: fan-out por keyword).
- MCP transporte remoto com auth/authz/abuse-protection.
- Execução contínua da memória de investigação entre processos
  (hoje: JSONL por investigação, sem cross-session ranking).
- Evals com LLM-as-judge opcional além do harness determinístico.
- Export do InvestigationReport como bundle forge-contracts/1.
- Human-in-the-loop real (fila de aprovações persistida).
