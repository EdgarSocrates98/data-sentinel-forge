# Cycle 08.2 — Relatório Final: Universal Portable Installer & Forge Ecosystem Compatibility

Specs: ds-0109 → ds-0118 (Loop Factory). Commits: `6377e17..HEAD` sobre `main`.

## 1. SHA da main

`76a6521` (HEAD no momento da escrita; range do ciclo `6377e17..76a6521` + ds-0118 pendente de commit).

## 2. Matriz de paridade

Auditoria registrada em `docs/cycles/cycle-08-2-parity-audit.md`. Achado
central: as Forjas irmãs vendoram um **installkit canônico**
(`the-forge/scripts/installkit/forge_installkit.py`) — o mesmo padrão
foi adotado, garantindo paridade estrutural de lifecycle.

## 3. Arquitetura de instalação

`src/data_sentinel/_installkit.py` (vendored, byte-idêntico ao upstream,
drift-checked via `_SOURCE_SHA256`, excluído de lint/type) + facade
tipada em `src/data_sentinel/installation/` (`service.py`, `hosts.py`,
`assets.py`, `contracts.py`, `ownership.py`, `planner.py`). Ledger
sha256 = única fonte de verdade para uninstall/repair.

## 4. CLI interativa

`data-sentinel install` — prompts Typer nativos (sem dep `rich`);
não-TTY exige `--yes`. Lifecycle: `status`, `doctor`, `repair`,
`uninstall [--purge]`, `env`, `mcp-verify`, `manifest [--agentic]`.

## 5. Perfis

`minimal` / `recommended` / `full` (`--profile`), override fino por
`--components` CSV; `--gateway economy|balanced|deep` advisory —
registrado no receipt, nunca altera limites de segurança. `off`
recusado (`FORGE-INSTALL-PROFILE-UNKNOWN`).

## 6. Escopos

`project` (state em `.data-sentinel/install`), `workspace`, `user`
(home do host). `--root` para override. Resolução via kit.

## 7. Host adapters

`claude` (`.claude/skills|agents`), `devin` (`.devin/` + espelho
`.agents/`), `codex` (`.agents/` + `.codex/agents/*.toml`), `copilot`
(`.github/skills|agents/*.agent.md`), `cursor` — **declarado sem
adapter de catálogo**: nenhum SKILL.md renderizado, limitação honesta.
Layout auditado contra os espelhos reais das Forjas irmãs.

## 8. Skills

5 skills versionadas na wheel (`data-sentinel-investigate`,
`data-sentinel-spark-plan`, `data-sentinel-sql-review`,
`data-sentinel-quality-drift`, `data-sentinel-report`), pt-BR,
frontmatter curto, disclosure progressivo, comandos verificados contra
o CLI real.

## 9. Agents

3 manifests (`sentinel-investigator`, `sentinel-spark-specialist`,
`sentinel-reviewer`) renderizados por host (Markdown; TOML no Codex).
Sem tools não declarados, sem permissões cloud por padrão.

## 10. MCP

`.mcp.json` merged preservando servidores estrangeiros (chaves
`_forge_managed`). Comando resolvido para path absoluto do executável.
Handshake real verificado: initialize + tools/list → **20 tools**.
Sem extra `mcp` → `UNVERIFIED` honesto. Codex project-scope →
`NOT_APPLICABLE` (Codex não consome `.mcp.json` de projeto).

## 11. Bootstrap

`src/data_sentinel/__main__.py` — `python -m data_sentinel` funciona
de wheel e de source tree.

## 12. Source methods

`install env` → `source.method`: repo / copied-tree / installed /
editable, detectado honestamente.

## 13. Integrity manifests

`installation/assets/MANIFEST.sha256` pinna todo arquivo do catálogo;
missing/extra/tampered → `FORGE-INSTALL-VERIFY-FAILED` (fail closed).

## 14. Receipts

`forge/InstallReceipt/v1` por operação; ledger sha256 + journal de
rollback no state dir.

## 15. Repair

`install repair` restaura managed files byte-identical a partir dos
assets da wheel; arquivos estranhos são recusados (teste dedicado).

## 16. Update

Reinstall idempotente — arquivos idênticos viram `unchanged`/`adopted`;
drift visível em `install status` (`modified`/`missing`).

## 17. Uninstall

Remove apenas paths do ledger; `--purge` remove o state dir. Arquivos
do usuário e servidores MCP estrangeiros preservados (E2E dedicado).

## 18. Forge CLI compatibility

`forge.json` + `forge.agentic.json` (`forge/SpecialistAgenticManifest/v1`)
na raiz; workflows usam só comandos reais do CLI; doc de registro em
`docs/integrations/forge-cli-registration.md`. Teste de drift garante
paridade com a saída programática de `install manifest`.

## 19. The Forge discovery

Registry neutro `~/.forge/installations`; `install env` lista
instalações registradas. Sentinel permanece independente — The Forge é
integração opcional, nunca dependência.

## 20. Testes

**+93 testes de instalação** (unit + E2E matrix §13.3: scopes, profiles,
gateway, hosts, components, pre-existing files, lifecycle, refusal
paths, MCP, secrets-scan, env report) + golden plan matrix §13.4
(30 planos scope x host x profile, 160 arquivos planejados, determinístico
via sha256). Suíte total: 1023 pytest (full suite verde).

## 21. CI

Matrix existente ubuntu/macos/windows × py3.11/3.12 cobre §13.5 —
os testes de instalação rodam lá. Job `minimal-install` (ds-0100)
garante core sem extras.

## 22. Segurança (§14)

P0 cobertos por teste: sobrescrita de arquivo do usuário (backup+
receipt), exclusão de não-gerenciado (ledger-only uninstall), instalação
fora de escopo (refusal de path `..`/absoluto em `_render_assets`),
dry-run sem mutação, segredos fora de receipts (scan E2E), rollback por
journal, subprocess confinado a `_spawn`/`spawn_ok`, MCP read-only.
P1: host mapping auditado, handshake real, wheel content verificado,
reinstall idempotente, drift detection.

## 23. Cross-platform

CI em 3 OSes × 2 Pythons. Encoding UTF-8 explícito em todo I/O
(corrigido no 08.1 após mojibake cp1252 real no Windows).

## 24. Packaging

Wheel inclui os 8 assets + `MANIFEST.sha256` (inspeção verificada).
`pyproject.toml` exclui `_installkit.py` de lint/type.

## 25. Documentação

25 guias pt-BR em `docs/installation/` (quickstart, escopos, profiles,
componentes, 4 hosts, MCP, forge-cli, the-forge, offline, 3 OSes,
gitless, update-repair, uninstall, troubleshooting, security,
compatibility-matrix). `docs/installation.md` atualizado com lifecycle
agentic + env vars + notas corporativas. README atualizado.

## 26. Known limitations

- PyPI não publicado — instalação por wheel/source apenas.
- Cursor: sem adapter de catálogo (declarado).
- Codex: `.mcp.json` de projeto é NOT_APPLICABLE (limitação do host).
- Windows/macOS homologados via CI; verificação local é Linux.
- `--gateway` é advisory — não altera comportamento de segurança.
- Versão 0.1.0; sem publish.

## 27. P0/P1/P2

Todos os P0 verificados por teste (§22). P1 cobertos. P2 (UX do
instalador, novos hosts, templates extras, auto-discovery) ficam como
backlog explícito.

### Revisão independente (ds-0118)

Revisor independente sobre o diff `d36a00b..HEAD`: kit verificado
**byte-idêntico** ao upstream (1.732 linhas, stamp `_SOURCE_SHA256`
consistente com as 7 cópias vendored); MANIFEST.sha256 íntegro.
Achados e correções aplicadas:

| Sev | Achado | Fix |
|---|---|---|
| H1 | `uninstall --scope user --purge` apagaria `~/.data-sentinel/{sentinel.db,session-token}` | `user_state_dir` aninhado em `install/`; teste de regressão |
| H2 | prompt interativo oferecia nomes de componente que o engine recusa | prompt alinhado a `OPTIONAL_COMPONENTS`; teste |
| M1 | `distribution` divergia do nome real do pacote | `data-sentinel` em spec/manifests/registry |
| M2 | registry `mcp.server_name` ≠ chave real em `.mcp.json` | `data-sentinel` |
| M3 | registry nunca deregistrado; `install_root` fantasma; writes fora do lock | deregister no uninstall; `install_root=ctx.root`; dentro do lock |
| M4 | `.mcp.json` ausente do plano | `planned_mcp` no dry-run |
| M5 | `install --yes` exit 0 com `verification=FAIL` | exit 1; teste com `.mcp.json` malformado |
| M6 | env report omitia knobs `DATA_SENTINEL_<campo>` | derivado de `SentinelConfig.model_fields` |
| M7 | planner recusava arquivo estrangeiro byte-idêntico | compara sha256 → SKIP vs REFUSE real |
| M8 | `uninstall --dry-run` mostrava drift, não remoções | `would_remove` = ledger `owned_paths` |
| M9 | uninstall/repair sem gate de confirmação | `--yes`/TTY confirm, simétrico ao install |
| M10 | gaps de teste | user-purge, registry deregister, malformed mcp, host none, interactive, stamp |
| M11 | `cursor` listado como adapter no manifest | `host_partial` declara marker+mcp only |
| M12 | `--scope user` escrevia `~/AGENTS.md` que nenhum host lê | markers omitidos no user scope |

LOWs restantes: backlog documentado (planner `_detect_source` duplicado,
receipt escrito duas vezes, `_life` expõe flags ignorados, receipt
secret-scan guard não ligado ao fluxo kit, `env` hard-fail fora de repo).

## 28. Acceptance decision

**APPROVED WITH RESTRICTIONS.**

Homologado: instalação real multi-host em tmp roots, lifecycle
completo (install→status→doctor→repair→uninstall), wheel packaging,
handshake MCP real, integridade de catálogo, paridade estrutural com o
installkit canônico. Restrições: PyPI não exercitado (não publicado),
homologação macOS/Windows delegada à matrix CI, integração real com
The Forge/forge-cli limitada a manifests + docs de registro (sem teste
contra um forge-cli real instalado).
