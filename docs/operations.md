# Operações (Cycle 07)

## Persistência

Investigações e eventos SSE ficam em SQLite local
(`~/.data-sentinel/sentinel.db` por padrão; `DATA_SENTINEL_DB` para
override). Sem ORM, sem processo de rede — stdlib `sqlite3`
parametrizado. Conteúdo bruto de arquivos nunca é persistido;
somente relatórios serializados e eventos estruturados.

## Retenção

`InvestigationStore.prune(older_than_s=..., limit=...)` remove
registros antigos de forma autorizada e auditável. Resumos de
memória (`investigation_memory`) guardam apenas hash + excerto
sanitizado de 120 chars — nunca o problema integral nem segredos.

## Backup & restore

O banco é um arquivo único SQLite:

- **Backup**: copiar `sentinel.db` com o servidor parado, ou
  `sqlite3 sentinel.db ".backup copia.db"` a quente.
- **Restore**: repor o arquivo no caminho configurado e reiniciar.
  O schema é criado via `CREATE TABLE IF NOT EXISTS` — bancos de
  versões anteriores sem a tabela `investigation_memory` passam pela
  criação automática na primeira escrita (migração segura, sem
  destruição).

## Watch & alerting

Watches são criados **desabilitados** via API — nenhum monitoramento
começa sem ação explícita (POST `/watches/{id}/run`). `source=aws`
é rejeitado na API: polling AWS exige opt-in via CLI com profile,
region, escopo e budget declarados. Cooldown/dedup/recovery estão
no `AlertEngine`; `WatchRuntime` (thread local) tem intervalo
mínimo, limite de watches, backoff e cancelamento.

## Remediação supervisionada

Planos passam por DRAFT → VALIDATED → AWAITING_APPROVAL →
APPROVED/REJECTED/EXPIRED. Aprovação exige `approver` não vazio e
**nunca** executa nada sozinha. `execute-local` só aplica ações do
`LOCAL_ACTION_ALLOWLIST` (update_watch_threshold, suppress_alert,
escalate_notification) — nenhuma ação cloud existe no executor.
Dry-run devolve prévia estruturada sem aplicar nada.

## Custos

Estimativas usam tabela estática de preços declarada
(`price_source`, região, assumptions, exclusions). `what_if`
compara cenários sem afirmar resultado real — sempre rotulado
como simulação.
