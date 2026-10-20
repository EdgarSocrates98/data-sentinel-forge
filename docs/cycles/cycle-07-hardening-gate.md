# Cycle 07 — Hardening Gate (ds-0080)

Baseline: `eeb9348` → work in progress.

## §1.2 API Authentication — DONE
- `SessionAuth`: Bearer token alta entropia (`secrets.token_urlsafe(32)`),
  TTL 4h com rotação automática, persistido em `~/.data-sentinel/session-token`
  (chmod 600) ou env `DATA_SENTINEL_TOKEN`. Sem segredos em URLs/logs.
- Middleware `bearer_auth`: exige `Authorization: Bearer` em `/api/v1/*`
  exceto `/health` e docs.
- Middleware `local_guard`: Host não-local → 403 (DNS rebinding);
  mutações com Origin cross-site → 403 (CSRF).
- `serve` imprime o token no boot; audit log registra 401/403/429.

## §1.4 Evidence Propagation — DONE
- `tools/registry._run_diagnostics` agora emite `outcome.evidence`
  (antes descartava).
- `investigator` coleta, valida e deduplica evidência por `evidence_id`;
  `rep.evidence` populado — 0 dangling refs verificado em teste real.

## §1.5 Token Redaction — DONE
- Classificação por schema: `_CREDENTIAL_KEYS` (access/refresh/id/session
  token, secrets, keys, credentials) sempre mascarados;
  `_SAFE_TOKEN_KEYS` (tokens_used, token_usage, input/output_tokens,
  token_budget…) preservados; fallback por substring para compostos
  (password/secret/credential/private_key/access_key).

## §1.3 Angular Security Upgrade — delegado (em curso)
## §1.6 Reproducible Browser Tests — delegado (em curso)

## Verificação
749 passed / 4 env-gated skips; ruff+mypy clean; 25 testes API+segurança.
