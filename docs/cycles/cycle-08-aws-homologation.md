# Cycle 08 — Homologação AWS Real (08.2 / §3.6)

## Status: BLOCKED_EXTERNAL

Não há credenciais AWS non-prod autorizadas no ambiente. Por decisão
do Grill Gate (ds-009x #2) e §3.6 do prompt, o bloqueio é registrado
como tal — **sem mascaramento por mocks**.

## O que existe (verificado no código, não na nuvem)

| Conector | Ações permitidas | Verificação |
|---|---|---|
| Glue | allowlist read-only explícita — mutações rejeitadas antes de qualquer call | teste estrutural |
| CloudWatch Logs | allowlist read-only | teste estrutural |
| CloudWatch Metrics | allowlist read-only | teste estrutural |
| EMR | allowlist de 8 ações read-only | teste estrutural |

## Testes env-gated (4 skips na suíte)

- `tests/security/test_security_cycle3.py` — requer credenciais
  non-prod via env
- `tests/security/test_emr_security.py` — idem
- `tests/e2e/test_lakehouse_e2e.py` — idem
- `tests/e2e/test_scenarios.py` — idem

## Para desbloquear

1. Credenciais de conta **non-prod** autorizada (env `AWS_PROFILE` +
   `AWS_REGION` explícitos).
2. Scope de recursos declarado.
3. `DATA_SENTINEL_AWS_E2E=1` (ou o gate usado pelos testes) para
   executar a suíte env-gated.
4. Revisar allowlist antes de rodar — permanece read-only.

Nada aqui executa jobs, muta recursos ou baixa dados em massa.
