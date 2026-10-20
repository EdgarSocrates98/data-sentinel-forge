# Backlog — Cycle 08

1. Persistir snapshots/watches/plans no SQLite (hoje in-memory na API).
2. Coletores AWS opt-in: Glue GetJobRun, EMR DescribeCluster,
   CloudWatch GetMetricData — via CLI com profile/region/budget.
3. Sazonalidade com histórico suficiente (hoje: conservador).
4. Multi-hop sequencial entre especialistas — só se demonstrar
   ganho mensurável sobre roteamento determinístico (§9.6).
5. Notificações externas (webhook/email) com allowlist de destinos.
6. Vitest no frontend (resolve advisories dev-only via Karma).
7. Export de RemediationPlan como bundle Forge-consumable completo
   (incluindo assinatura de integridade).
8. Doctor findings correlacionados dentro de evaluate_hypothesis.
