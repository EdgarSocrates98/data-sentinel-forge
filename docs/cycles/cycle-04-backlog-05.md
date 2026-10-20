# Backlog proposto — Cycle 05

1. **Impacto coluna-a-coluna**: usar facet columnLineage para filtrar
   downstream por colunas afetadas (reduce falso-positivo do grafo dataset).
2. **Execução real de regras**: engine nativa opcional (DuckDB/SQL) para
   avaliar contratos contra dados reais quando explicitamente solicitado.
3. **API/MCP servers**: implementar os contratos de readiness dos Cycles 02+
   (hoje só contratos).
4. **Marquez/OpenLineage live polling**: ingestão contínua quando houver
   backend disponível (hoje: arquivo/export).
5. **Baselines persistidas**: snapshots de perfis em store para drift
   longitudinal sem fixtures.
6. **CI remota verde**: desbloqueio depende de billing/privacidade do repo,
   não de código.
7. **AWS real homologation**: credenciais ausentes neste ambiente; guia
   §12 do Cycle 03 segue válido.
8. **Doctor bundle consumer**: fazer o Doctor Data/API ler o bundle
   exportado do Sentinel (direção inversa do adapter atual).
