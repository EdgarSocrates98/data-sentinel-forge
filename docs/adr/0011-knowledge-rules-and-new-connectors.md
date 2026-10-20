# ADR 0011 — Knowledge rules YAML e novos conectores read-only

- Status: aceito
- Data: Cycle 03 (grill gate)

## Contexto

O Cycle 03 exige uma base de compatibilidade versionada (§8) e diagnóstico
de acesso que toca Lake Formation, IAM, S3 e KMS (§5–§6).

## Decisões

1. **Knowledge rules em YAML via PyYAML** — formato do exemplo do prompt,
   humano-editável com comentários e histórico por regra. PyYAML entra
   como dependência de runtime (leve, madura). Regras vivem em
   `data_sentinel/knowledge/rules/*.yaml` como **package data** — o wheel
   carrega a base (§8.4 exige funcionar fora do checkout).
2. **Novos conectores read-only**: `connectors/aws/{lakeformation,iam,s3,
   kms,sts}` seguindo o padrão ds-0011/0012 — `ALLOWED_ACTIONS` explícita
   (`Get*`/`Describe*`/`List*`/`Simulate*`), extra `[aws]`, recusa offline,
   Stubber nos testes.
3. **IAM SimulatePrincipalPolicy entra na allowlist** — é API não-mutante
   (decisão do grill); suas limitações conhecidas (resource policies,
   SCPs, session context, Lake Formation) são documentadas nos resultados,
   nunca apresentadas como validação real.
4. **Homologação AWS real**: tentar com credenciais autorizadas não-prod
   env-gated; ambiente atual não tem credenciais — se persistir, a
   homologação real registra BLOCKED e os simulados seguem executáveis.

## Consequências

- `pyproject.toml` ganha `pyyaml` runtime; `uv.lock` muda.
- Rule engine não depende de rede nem de paths do repo —
  `importlib.resources` resolve os YAMLs dentro do pacote.
- Regras sem fonte/versão/data/owner falham na validação de schema —
  compatibilidade sem evidência não entra na base.
