# Segurança do instalador

## P0 — propriedades garantidas por teste

- Arquivo do usuário nunca sobrescrito (conflito → backup + receipt ou recusa)
- Uninstall remove só o que o ledger sha256 registrou
- Writes confinados ao scope root — path `..`/absoluto recusado antes do join
- Dry-run não cria state dir, lock, receipt ou qualquer arquivo
- Receipts/ledgers não contêm segredos (scan no E2E matrix)
- Assets verificados por `MANIFEST.sha256` — adulteração fecha com refusal
- Sem execução de fonte remota; subprocess confinado a `_spawn()`
  (mcp-verify/update) gated por `spawn_ok`
- Rollback por journal em falha parcial — restaura o estado anterior

## P1 — cobertos

- Host mapping auditado por layout real de cada plataforma
- Handshake MCP real (20 tools) ou `UNVERIFIED` honesto
- Wheel carrega todos os assets (verificação de conteúdo)
- Reinstall idempotente; update com drift detectável via status

## Relato de problemas

`SECURITY.md` na raiz do repositório.
