# Cycle 07 — Operações Autônomas: Relatório Final

**Decisão: APPROVED WITH RESTRICTIONS**

## Escopo entregue

| Fase | Entrega | Status |
|---|---|---|
| 07.0 | Gate: bearer auth+rotação, Origin/DNS-rebinding, evidência propagada no report, redação por classificação de schema, Angular 19→20.3 | VERIFIED |
| 07.1 | Persistência SQLite (`persistence/investigations.py`): lifecycle, recovery, replay por seq, retention, concorrência | VERIFIED |
| 07.2 | Histórico: `ExecutionSnapshot`, comparabilidade, baselines (previous/rolling/median/reference/cohort) | VERIFIED |
| 07.3 | Regressão: thresholds abs/rel, mediana+MAD, trend; rótulo `suspected_cause`, nunca causa confirmada | VERIFIED |
| 07.4 | Watch/alerting: engine dedup/cooldown/recovery/missing-data-INFO; runtime local bounded | VERIFIED |
| 07.5 | Custo: Glue DPU-hour + what-if com premissas explícitas | VERIFIED |
| 07.6 | Remediação: plano + workflow de aprovação + dry-run + executor local allowlist | VERIFIED |
| 07.7 | Control Center Operations UI | ver ds-0087 |
| 07.8 | Agentic ops: triggers, rótulos §9.4, memória §9.5 | VERIFIED |
| 07.9 | Segurança/a11y/perf + 30 golden datasets + E2E A–N | VERIFIED (K/L via Playwright) |

## Verificação

- **871 pytest passed, 4 skipped** (env-gated AWS real — sem
  credenciais não-prod no ambiente).
- `ruff check src tests`: clean. `mypy src`: 151 arquivos, 0 erros.
- E2E dedicado `tests/e2e/test_cycle7_ops.py` (14 cenários) +
  golden runner `test_cycle7_golden.py` (30 cenários com ground
  truth em `fixtures/evals/cycle7/`).
- Benchmarks reais (`docs/evidence/benchmarks-cycle7.json`):
  200 investigações persistidas em ~1.97s; replay de 1000 eventos
  em ~7ms; watch eval 100×20 snaps em ~6.5ms.

## Regras duras honradas

- Watch **nunca** auto-inicia via API; `source=aws` rejeitado no
  endpoint (opt-in CLI only).
- Aprovação de remediação **nunca** executa cloud; executor local
  restrito a `LOCAL_ACTION_ALLOWLIST` (3 ações de estado local).
- Hipóteses rotuladas observed/associated/probable/unknown —
  `CONFIRMED` deliberadamente irrepresentável na camada §9.4.
- Custos sempre ESTIMATED com `price_source` declarado.
- Memória de agente: hash sha256 + excerto 120 chars sanitizado;
  nenhum documento integral nem segredo persistido.
- Nenhum método DELETE/PUT na API (invariante de não-cancelamento).

## Restrições declaradas

- Snapshots/watches/plans na API são **in-memory** por processo
  (histórico de investigações é persistente); persistência desses
  registros é backlog.
- WebKit Playwright: host sem `libavif16` — Chromium+Firefox cobertos.
- 12 advisories npm residuais: cadeias dev-only via `braces` sem fix
  upstream (detalhado em `frontend/SECURITY-UPGRADE.md`).
- Multi-hop entre especialistas: avaliado e **não implementado**
  (§9.6 — roteamento determinístico cobre; loops proibidos).
- CI remota: segue bloqueada por billing do repo privado.

## Backlog Cycle 08 (docs/cycles/cycle-07-backlog-08.md)
