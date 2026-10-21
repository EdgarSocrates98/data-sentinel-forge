# Cycle 08.2 — Forge Installer Parity Audit

Audit for spec `ds-0109` (factory/specs/active/ds-0109.md), feeding prompt
`prompt_evo_cycle8.2.md` §1.2–§1.3 (auditoria dos instaladores existentes +
matriz de paridade). Read-only audit of sibling checkouts under
`/home/edgar/Documentos/projetos/forjas/`; no code was modified anywhere.

## 0. Method and coverage (honest statement)

Inspected in full (read every relevant file): `forge-cli` installer surface
(`src/install.ts`, `native-install.ts`, `hosts/` all five adapters,
`mcp/handshake.ts`, `lifecycle.ts`, `manifest.ts`, `discovery.ts`,
`planner.ts`, `artifacts.ts`, `registry/catalog.ts` + receipt interfaces in
`registry/install.ts`, `source/detect.ts` head, `source/install.ts` head,
`contracts/schemas/*.json`, `constants/repos.ts`); the canonical
`forge_installkit.py` (all 1732 lines, via the vendored copy in
spark-forge-aws — byte-identical `_SOURCE_SHA256` across all copies);
`forge_bootstrap.py` header + pipeline docstring; `install.sh`,
`install.ps1`, `install.windows.sh` headers; the per-forge `install/`
packages (`service.py` in the-forge / api-forge / forge-doctor-api /
forge-doctor-data / platform-forge / spark-forge-azure; `install/cli.py`,
`install/hosts.py`, `install/lifecycle.py` head in spark-forge-aws);
`forge.json` and `forge.agentic.json` of every Python forge; host-asset
directory inventories (`find` counts) in every sibling; the-forge
`install/render.py`, `install/providers.py` head, `agentic/agents/*.toml`
listing, `adapters/` listing; `vendor.py` docstring; data-sentinel's own
`installation/` package (3 files, read in full), `cli/__init__.py` command
inventory, `mcp_server.py`, `agents/specialists.py`, `pyproject.toml`.

Sampled only (headers/listings, not full reads): `integrate/` package of
spark-forge-aws (writer.py is 1041 lines — read docstrings/structure only),
`registry/install.ts` mid-sections, `source/install.ts` mid-sections,
`the-forge/install/service.py` tail (update/auto paths), platform-forge
`install/service.py` mid-sections, `forge-doctor-api/scripts/forge_hosts.py`
and `forge_install.py` (headers only).

Not inspected: forge-cli `tests/` details, `menu.ts`/`wizard.ts` internals,
forge-portal internals beyond the top-level listing, eval suites. Where a
claim rests on sampling rather than full reading, it is marked below.

---

## 1. Parity matrix

Legend: **YES** implemented · **PARTIAL** exists but narrower than the
contract · **NO** absent · **NA** not applicable (role/type of repo).
"Sibling forges" column names which forges have the capability
(TF=the-forge, SFA=spark-forge-aws, SFZ=spark-forge-azure, AF=api-forge,
PF=platform-forge, FDA=forge-doctor-api, FDD=forge-doctor-data,
FP=forge-portal). DS = data-sentinel at HEAD (incl. uncommitted ds-0109
files under `src/data_sentinel/installation/`).

| Capability | forge-cli | Sibling forges that have it | data-sentinel TODAY |
|---|---|---|---|
| Native install CLI verb (`<cli> install`) | YES (`install <forges\|<dir>>`, `self install`) | TF `theforge install apply`, SFA `sparkforge-aws install`, SFZ `sparkforge-azure install`, AF `apiforge install`, PF `platformforge install`, FDA `forge-doctor-api install` (pkg) + `scripts/forge_install.py`, FDD `forge-doctor-data install` | **NO** — no `install` command in `cli/__init__.py` |
| Interactive/guided installer | YES (`wizard.ts`, `menu.ts`, `prompts.ts`) | SFA (`ui/wizard.py` + `approve_plan`), AF (`cli_install_pretty.py`) | **NO** |
| Non-interactive flags (`--scope/--profile/--components/--host/--gateway-profile/--yes/--dry-run/--root`) | YES (validates in `native-install.ts`, forwards to native installers) | TF, SFA, SFZ, AF, PF, FDA, FDD (all via installkit CLI wrappers) | **NO** |
| Dry-run (plan-only, zero writes) | YES (`planSelfInstall`, `--plan`, `applyHostPlan(dryRun)`, plan hash verification) | YES — `plan()` never writes; `apply_install` requires `approved` or `dry_run` (installkit: `E_NOTAPPROVED`) | PARTIAL — `planner.py` exists (plan-only, deterministic `plan_id`), no applier yet |
| Scopes: project / workspace / user | YES (declared constants; host adapters are user-scope; workspace = targetDir) | YES — installkit `resolve_scope()` w/ VCS-root detection, workspace markers (`forge.workspace.yaml`, `.forge-workspace`, workspace pyproject), `state_dir_for()`; user scope = `$HOME` + `user_state_dir` | PARTIAL — `InstallScope` enum declared; no resolution logic |
| Profiles: minimal / recommended / full | YES (`PROFILES` in `native-install.ts`) | YES — `profile_asset_kinds()` in installkit | PARTIAL — `InstallProfile` enum declared only |
| Gateway profiles: economy / balanced / deep | YES (`GATEWAY_PROFILES`, forwarded as flag) | SFA, SFZ, AF, FDA, FDD (persisted to `components.json` as `execution_profile`); TF accepts flag | PARTIAL — `GatewayProfile` enum declared only |
| Ownership ledger (per-file sha256, managed vs adopted/foreign) | YES (receipts `managed_artifacts`, state.json `previousHead`) | YES — installkit `Ledger` (`install-ledger.json`, `forge/InstallLedger/v1`), `adopted` never deleted, sha256 re-verify before unlink | PARTIAL — `ownership.py` `OwnershipLedger` (`.data-sentinel/installation-ledger.json`) exists; no drift/adopt kinds |
| Receipts (`forge/InstallReceipt/v1` + receipt store) | YES (`install.json` under `~/.forge-cli/forges/<name>/`, `ForgeOperationReceipt/v1` schema) | YES — `<state_dir>/receipts/<op>-<ts>.json` via `_write_receipt`; receipt schema embedded in installkit | PARTIAL — `InstallReceipt` model + `assert_no_secrets`; no store |
| Install lock (concurrency refusal) | YES (`acquireForgeLock` in `registry/install.ts`) | YES — installkit `_Lock` O_EXCL + stale reclaim | **NO** |
| Marker blocks in AGENTS.md/CLAUDE.md (`<tag>:managed:begin/end`) | NA (CLI, not a forge product) | YES — installkit `apply_marker_block`/`remove_marker_block`; all Python forges set `marker_files`/`marker_body` | **NO** — no AGENTS.md/CLAUDE.md at repo root at all |
| Managed `.mcp.json` key (`mcpServers.<name>` + `_forge_managed`) | YES (`mergedMcpConfig`, `hasMcpEntry`) | YES — installkit `mcp_set`/`mcp_unset` | **NO** |
| Host adapter: Claude | YES (`hosts/claude.ts` — `~/.claude.json` merge-json, `claude mcp add` hint) | SFA (`.claude/skills`,`.claude/agents` + plugin.json), SFZ, AF, PF, TF (skills); FDA/FDD declare host but ship no mirrors | **NO** |
| Host adapter: Codex | YES (`hosts/codex.ts` — TOML append `~/.codex/config.toml`, `codex login status` auth probe) | SFA (`.codex/agents/*.toml`, `.agents/skills`), SFZ, AF, PF, TF (`.codex/agents` TOML) | **NO** |
| Host adapter: Devin | YES (`hosts/devin.ts` — detect only; `planIntegration`→null, honest "no documented MCP surface") | SFA (`.devin/`, `.agents/`), AF, PF; FDA/FDD declare only | **NO** |
| Host adapter: Copilot | YES (`hosts/copilot.ts` — only if `~/.copilot/mcp-config.json` exists) | SFA (`.github/agents`,`.github/skills`), AF, PF | **NO** |
| Host adapter: Cursor | YES (`hosts/cursor.ts` — `~/.cursor/mcp.json` merge-json) | **NO** sibling ships cursor assets | **NO** |
| Canonical skills tree + host mirrors | NA (installer only) | SFA `skills/`(60)+mirrors (`.claude`,`.agents`,`.codex`,`.github`), SFZ `skills/`(22), AF `.agents/skills`(14)+`.devin/skills`(15)+`.github/skills`(14), TF `.claude/.agents/.devin/skills`(33 each) | **NO** — zero `SKILL.md` anywhere |
| Canonical agents tree + host mirrors | NA | SFA `agents/`(14 coord +5 executors)+mirrors, SFZ `agents/`(40), AF `agents/`(25 coordinators, `apiforge agents sync`), PF `agents/`(41, `platformforge agents sync`), TF `agentic/agents/*.toml` (8, AgentSpec/v1) | PARTIAL — `agents/specialists.py` registry of 18 specialists (in-code `AgentDescriptor`s), no host-readable assets |
| Agent teams | NA | SFA (executor fan-out, `agent-teams` in SFZ), PF `agents/` team specs | **NO** |
| MCP server runtime | NA | SFA `mcp serve` (stdio+http), SFZ `mcp serve`, AF `apiforge-mcp` script, PF `platformforge-mcp`, FDA/FDD `<cli> mcp`; TF none (control plane) | YES — `data_sentinel/mcp_server.py` stdio server over `mcp` SDK (extra `mcp`); `data-sentinel mcp serve` + `python -m data_sentinel.mcp_server` |
| MCP post-install validation (real handshake) | YES (`mcp/handshake.ts`: levels INSTALLED→EXECUTABLE→INITIALIZED→TOOLS_DISCOVERED→SAFE_TOOL_CALLED→HOST_VERIFIED; safe-tools allowlist from catalog) | YES — installkit `mcp_verify()` (initialize→initialized→tools/list→optional tools/call via `mcp_verify_tool`); each forge declares a no-arg read-only verify tool | **NO** — server exists; no handshake validator (integration test `tests/integration/test_mcp_stdio.py` exists) |
| status verb | YES (`status.ts`, `forge-cli status`) | YES — installkit `status()` (drift report `forge/InstallationHealth/v1`) | **NO** — `data-sentinel doctor` exists (env checks) but no install-status |
| doctor (install-health) verb | YES (`doctor.ts`, `doctor2/`) | YES — installkit `doctor()` (ledger + drift + mcp-config + mcp-handshake + repairable flags) | PARTIAL — `data-sentinel doctor` checks env only (line 313 `cli/__init__.py`); name-collision risk noted in §12 of prompt |
| repair verb | YES (`heal/` package, `repair` flows) | YES — installkit `repair()` re-asserts drifted managed content, heals marker blocks/mcp key, skips foreign | **NO** |
| update verb | YES (`uninstall`/`rollback`/`update` flows; `maintenance.ts`) | YES — `<cli> install update`/`update` → pinned-version pip upgrade via registered venv; `latest` refused | **NO** |
| uninstall verb | YES (refusals: symlink/non-git/remote-mismatch/dirty; backups first) | YES — installkit `uninstall()` removes only `managed` entries, excises markers, unsets mcp key, prunes empty dirs, `--purge` removes state | **NO** |
| Bootstrap scripts (`install.sh`/`install.ps1`/`install.windows.sh`/`setup.sh`/`setup.ps1`) | YES (`install.windows.sh` + dist self-install) | YES — identical vendored set in TF, SFA, SFZ, AF, PF, FDA, FDD (thin wrappers over `scripts/forge_bootstrap.py`) | **NO** — zero shell/ps1 scripts in repo |
| Vendored `forge_bootstrap.py` + `_installkit.py` | NA (orchestrator side) | YES — TF canonical (`scripts/installkit/`); vendored byte-identical (`_SOURCE_SHA256=bc189dd2ae0028ce`, 1732 lines) in SFA, SFZ, AF, PF, FDA, FDD | **NO** |
| `forge.json` (ForgeDescriptor/v1) | Reads it (`manifest.ts`, fail-closed validation) | YES — TF, SFA, SFZ, AF, PF, FDA, FDD all have root `forge.json` | **NO** |
| `forge.agentic.json` (SpecialistAgenticManifest/v1) | Detects as signal (`forge-manifest`) | YES — SFA, SFZ, AF, PF, FDA, FDD (TF does **not** ship one; it's the consumer/router) | **NO** |
| `~/.forge/installations/` registry (forge/InstallationManifest/v1) | Reads (forge-cli registry mirrors it via its own receipts) | YES — `register_installation()`/`installed_forges()`; `theforge install auto` delegates through it | **NO** |
| Source methods: PyPI wheel / local wheel / git / ZIP / copied dir / gitless | YES — registry install (PyPI), `--method git`, `install <dir>` with LocalForgeSourceDetection/v1 (8 states incl. GITLESS_*) | installkit bootstrap handles wheel/editable/git-checkout/gitless source kinds | PARTIAL — wheel+sdist build fine (`docs/installation.md` verified cycle-08); no gitless/ZIP path, no installer entry |
| Offline / locked install | YES (`registry install --offline --lock <file>`, `--no-index`, sha256-verified artifacts) | bootstrap `--allow-download` gate; offline = cached wheel | **NO** |
| Integrity manifest (forge/IntegrityManifest/v1) | YES (`portability/manifest.ts` + `bundle.ts`) | PARTIAL — forge.json `lab`/identity fields used by detection; asset integrity via ledger sha256 | **NO** |
| Permission refusals (FORGE-INSTALL-*) | YES (`errors.ts` FORGE-* codes) | YES — installkit `InstallError` kinds (E_SCOPE/E_HOST/E_PROFILE/E_PERM/E_NOTREPO/E_NOTAPPROVED/E_LOCKED/E_DRIFT/E_SPAWN/E_VERIFY/E_WRITE) | PARTIAL — planner emits `refusals` strings; no typed codes |
| The Forge provider adapter (subprocess+JSON contract) | NA | TF `adapters/`: apiforge, doctorapi, doctordata, platformforge, sparkforge_aws, sparkforge_azure — **no sentinel adapter** | **NO** |
| forge-cli catalogs (FORGE_REPOS + REGISTRY_PACKAGES) | — | All 7 Python forges + forge-portal present | **NO** — absent from both; cycle-12 docs record it as "excluded — other CLI owns it", "no installkit", "not published on PyPI nor npm" |
| Portal (Angular frontend) | NA | forge-portal (node kind, no native install); SFA/AF ship `portal/assets` in wheel | PARTIAL — `frontend/` Angular exists; no install integration |
| Windows support | YES (cmd shim, HKCU PATH, Git Bash route) | YES — `install.ps1`, `install.windows.sh`, `setup.ps1`; `_venv_bin`/`Scripts` handling | PARTIAL — pure-Python wheel (no native bins), but no scripts tested |
| Install lifecycle tests | YES (vitest suite) | YES — `tests/test_install*.py`, `test_installed_provenance.py`, `test_install_lifecycle.py` per forge | PARTIAL — `tests/unit/installation/test_contracts.py` (11 tests) for contracts/planner/ownership only |

---

## 2. Per-forge findings (evidence)

### 2.1 forge-cli (TypeScript, Node) — the central orchestrator

Best single source of truth for *how a forge gets installed and integrated*.

- **Self-install**: `src/install.ts` — copies bundled `index.mjs` to
  `~/.forge-cli/bin`, writes POSIX shim / `forge-cli.cmd`, injects guarded
  `# >>> forge-cli >>>` PATH blocks into `.bashrc`/`.zshrc`/`.profile`/fish
  config; Windows PATH via PowerShell `[Environment]::SetEnvironmentVariable`.
  `planSelfInstall`/`planSelfUninstall` = true dry-run planning;
  `uninstall()` strips only the guarded blocks + removes the dir
  (`src/install.ts:116-237`).
- **Registry install**: `src/registry/install.ts` (~1197 lines) — PyPI+venv
  default flow with receipts (`RegistryInstallReceipt`,
  `LocalInstallReceipt` interfaces at lines 90-194), `receiptPath()` =
  `~/.forge-cli/forges/<name>/install.json`, lifecycle lock
  (`acquireForgeLock`), offline `--lock` + `--no-index` path
  (`registry/lock.ts`), PyPI client (`pypi.ts`), version floors
  (`versions.ts`), shims (`shims.ts`).
- **Local source detection**: `src/source/detect.ts` — emits
  `forge/LocalForgeSourceDetection/v1` with 8 states (GIT_REPOSITORY,
  GIT_WORKTREE, GITLESS_VALID_FORGE, GITLESS_PARTIAL_FORGE, UNKNOWN_DIRECTORY,
  CONFLICTING_IDENTITY, INVALID_MANIFEST, UNTRUSTED_SOURCE), identity levels
  A/B/C, integrity verified/partial/unverified. Deterministic, offline, no
  spawn (`.git` is filesystem inspection).
- **Local install**: `src/source/install.ts` — runs the forge's own
  `setup.sh`/`install.sh`/`install.windows.sh` or falls back to
  `scripts/forge_bootstrap.py` (line ~241); never deletes source dir;
  uninstall removes only `managed_artifacts` (top-level entries created by
  the bootstrap, snapshotted pre/post).
- **Native delegation**: `src/native-install.ts` — canonical flag sets
  `PROFILES/SCOPES/HOSTS/GATEWAY_PROFILES`, `buildNativeInstall()` maps
  user flags onto each forge's documented `nativeInstall` command; without
  `--approve` it appends `--dry-run` (line 69-70). This is the contract a
  `data-sentinel install` must satisfy.
- **Host adapters**: `src/hosts/` — six-state model
  (absent→installed→configured→authenticated→integrated→validated, never
  flattened, `types.ts:18-29`); adapters for **claude** (merge-json into
  `~/.claude.json`, copyable `claude mcp add --scope user`), **codex**
  (TOML append `[mcp_servers.<id>]` to `~/.codex/config.toml`, auth probe
  `codex login status`), **devin** (detect only; `planIntegration`→null —
  honest hostUnsupported), **cursor** (`~/.cursor/mcp.json`), **copilot**
  (only when `~/.copilot/mcp-config.json` already exists). Shared
  `applyHostPlan` resolves all writes, backs up all targets to
  `~/.forge-cli/backups/hosts-<id>-<ts>/` with manifest.json + `.absent`
  sentinels, writes atomically, supports rollback
  (`hosts/types.ts:284-442`).
- **MCP verification**: `src/mcp/handshake.ts` — real stdio JSON-RPC
  handshake, cumulative levels; `tools/call` restricted to a maintainer
  allowlist (`mcp_safe_tools` in `registry/catalog.ts`), minimal input
  derived only from required fields with derivable defaults.
- **Planner**: `src/planner.ts` — `forge/ForgeOperationPlan/v1`,
  sha256 over canonical JSON, 15-min TTL, `verifyPlan` refuses
  expired/hash-mismatch.
- **Contracts**: `contracts/schemas/` — ForgeDescriptor, ForgeInstallContract,
  ForgeEnvironmentDiscovery, ForgeEnvironmentSchema, ForgeHealthReport,
  ForgeHostDescriptor, ForgeOperationPlan, ForgeOperationReceipt,
  LocalForgeSourceDetection, IntegrityManifest (impl in
  `src/portability/manifest.ts`). `src/manifest.ts` reads `forge.json`
  fail-closed (64KiB cap, SAFE_TOKEN regex, schema-validated when declared).
- **State ledger**: `src/artifacts.ts` — `.forge-cli/state.json`
  (per-repo status/phase/head/previousHead), guarded logs with
  `redactSecrets`, custom repos via `forge-cli.repos.json`.
- **Python discovery**: `src/env/python.ts` — `discoverPythons()` with
  `FORGE_PYTHON` env, floor `>=3.10`, 32 candidates max, verdict types.
- **Data Sentinel absent**: `data-sentinel`/`data_sentinel` appears in
  neither `src/constants/repos.ts` (FORGE_REPOS, 8 entries) nor
  `src/registry/catalog.ts` (REGISTRY_PACKAGES, 7 entries); only in
  `docs/cycle12/*` audit notes ("EXCLUDED — other CLI owns it", "not part
  of the vendored fleet (no installkit)", "published on neither PyPI nor
  npm").

### 2.2 the-forge — canonical InstallKit source + control plane

- **Canonical engine**: `scripts/installkit/forge_installkit.py` (1732
  lines, `_INSTALLKIT_VERSION="1.0.0"`, `_SOURCE_SHA256="canonical"`).
  Vendored per-forge as `<pkg>/_installkit.py`; all copies carry
  `bc189dd2ae0028ce` and are identical. `scripts/installkit/vendor.py`
  vendors `forge.json` + `setup.sh`/`setup.ps1` + `install.sh`/`install.ps1`/
  `install.windows.sh` + `scripts/forge_bootstrap.py` + `_installkit.py`;
  `vendor.py --check` detects drift.
- **InstallKit capabilities** (the shared engine every Python forge uses):
  `ForgeSpec`/`InstallContext` dataclasses; `Ledger` (sha256-keyed,
  `managed` vs adopted, kind-aware drift for `marker`/`mcp` entries);
  `_Lock` O_EXCL lockfile with stale reclaim; marker blocks
  `<!-- <tag>:managed:begin/end -->`; `mcp_set`/`mcp_unset` with
  `_forge_managed` tracking; `resolve_scope()` (VCS root, workspace
  markers, user=`$HOME`); `profile_asset_kinds`; `plan()` (pure) /
  `apply_install()` (journalled writes, pre-state backups under
  `<state>/backups/`, `_rollback_writes` on failure, adopted foreign files
  never touched, idempotent); `status`/`doctor`/`repair`/`uninstall`;
  `mcp_verify` real stdio handshake w/ `mcp_verify_tool` tools/call;
  `manifest_for`/`register_installation` → `~/.forge/installations/*.json`
  (forge/InstallationManifest/v1); `forge_portal_presence()`;
  `discover_projects`/`member_precedence` for workspace scope;
  `write_launcher`/`path_guidance` (~/.local/bin shims, .cmd on Windows);
  `spawn_ok` gate for subprocess-banned packages; refusal taxonomy
  FORGE-INSTALL-*.
- **Bootstrap**: `scripts/installkit/forge_bootstrap.py` (vendored as
  `scripts/forge_bootstrap.py`) — pipeline discover → resolve-python →
  create-venv → install-runtime → write-launcher → smoke-verify →
  register → report; driven by the repo's `forge.json`; `--dry-run`,
  `--editable`, `--allow-download`, `--python`, `FORGE_HOME_OVERRIDE`.
- **Own install service**: `src/theforge/install/service.py` (888 lines) —
  `install apply|status|doctor|repair|update|uninstall|auto|mcp-verify`;
  `install auto` delegates `install` to every forge registered in
  `~/.forge/installations/` via `_delegated_cmd` (supports each forge's
  `install_command` argv template with `{python}`/`{checkout}`/`{home}`/
  `{install_root}` placeholders — the hook for CLIs that can't run
  installkit in-package); `providers.py` registers user providers from
  local manifests (approval-gated, BEGIN/END managed block in user config).
- **Host rendering**: `src/theforge/install/render.py` — maps skills to
  `.claude/skills` (claude), `.devin/skills` (devin), `.github/skills`
  (copilot), `.agents/skills` (codex + shared mirror), agent TOMLs to
  `.codex/agents`. Canonical sources: checkout `.agents/skills/` +
  `agentic/agents/*.toml` (8 AgentSpec/v1 specs), fallback to
  `theforge/host_assets/` in wheel.
- **forge.json**: present; no `mcp_command` (control plane has no MCP).
- **forge.agentic.json**: **absent** — the-forge is the consumer/router of
  these manifests, not a provider of specialist workflows.
- **Providers**: `the-forge/adapters/{apiforge,doctorapi,doctordata,
  platformforge,sparkforge_aws,sparkforge_azure}` — separate distributions
  speaking the Forge Protocol (subprocess + JSON). No sentinel adapter.

### 2.3 spark-forge-aws — most complete per-forge implementation

- Vendored `_installkit.py` (`sparkforge_aws/_installkit.py`, identical
  hash) + `scripts/forge_bootstrap.py` + `scripts/forge_installkit.py` +
  all five shell entry points.
- `sparkforge_aws/install/` — `cli.py` (verbs: `install`, `status`,
  `install doctor`/`doctor install`, `repair`, `update`, `uninstall`,
  `mcp verify`, `mcp serve`; TTY-interactive approval via
  `ui/wizard.approve_plan`, JSON docs on pipes); `lifecycle.py`
  (ForgeSpec wiring: `mcp_command=(sys.executable,"-m",
  "sparkforge_aws.adapters.mcp","--transport","stdio")`,
  `mcp_verify_tool="sparkforge_aws_runtime_detect"`,
  `state_dir=".sparkforge_aws"`); `hosts.py` (project-scope host table:
  claude `.claude/{skills,agents}`, devin `.devin/{skills,agents}` +
  `.agents/` shared mirror, codex `.codex/agents/*.toml` + `.agents/skills`,
  copilot `.github/{agents,skills}`).
- `sparkforge_aws/integrate/` — user-scope (HOME) machinery: `hosts.py`
  (declarative host table with doc-source URLs per layout), `writer.py`
  (1041 lines, ownership/disco engine), `render.py` (759 lines, per-platform
  rendering), `conflict.py`, `claude.py` (plugin/marketplace layout),
  `sources.py` (content_root: checkout vs wheel `integrate/bundle/`).
- Host assets committed: `skills/`(60), `agents/`(14 coordinators + 5
  executors in `agents/executors/`), mirrors `.claude/`(60+19),
  `.agents/`(60+19), `.codex/agents/`(14 TOML), `.github/agents/`(19),
  `.devin/`(config.json, mcp_config.json), `.claude-plugin/plugin.json`.
- `forge.json` (forge_id `spark-forge-aws`, `mcp_command=[cli,mcp,serve]`,
  `extras=["mcp"]`, lab contract) + `forge.agentic.json`
  (SpecialistAgenticManifest/v1: 3 workflows, 1 skill, 1 coordinator,
  host_adapters=[claude,devin,codex,copilot]) + root `manifest.json`
  (catalog metadata: 60 skills, 148 tools, plugin path, parity.yaml).
- Wheel packaging: `pyproject.toml` `force-include` of `skills`→
  `sparkforge_aws/integrate/bundle/skills`, `agents`→`integrate/bundle/agents`,
  `rules/catalog`, `knowledge`, `portal/assets`, evals data — the
  install-from-wheel path the installer reads when there's no checkout.
- Codex/MCP honesty note: `install/lifecycle.py` +
  `_installkit.apply_install` emit `NOT_APPLICABLE` check when scope=project
  + host=codex (codex doesn't read project `.mcp.json` — observed on
  codex-cli 0.160.0).

### 2.4 spark-forge-azure

Same pattern, slimmer: `sparkforge_azure/install/service.py` (438 lines),
`cli/cmd_install.py`, vendored `_installkit.py` + scripts; host assets
`skills/`(22), `agents/`(40), `.claude/`, `.agents/` mirrors + `agent-teams/`
dir; `forge.json` (`forge_id=sparkforge-azure` — note: underscore form,
differs from repo name), `forge.agentic.json` (skills/agents arrays empty —
declaration exists, mirrors committed). `evals/parity/`, `evals/host_proof/`,
`evals/portability/` suites exist. `forge-cli` catalog flags include
`gateway-profile`.

### 2.5 api-forge

`src/apiforge/install/{service.py(310),render.py(151)}` over vendored
`_installkit.py`; `ForgeSpec` uses `mcp_command=("apiforge-mcp",)` +
`mcp_verify_tool="portable_status"`. `src/apiforge/host_assets/` —
`manifest.yaml` (schema `apiforge/host-assets/v1`), `templates/` (CLAUDE.md,
AGENTS.md, mcp_config.json templates), and wheel `force-include` of
`agents/`→`host_assets/agents` + `.agents/skills`→`host_assets/skills` —
the fallback read path when no checkout exists
(`install/render.py:content_dirs()`). Agents: `agents/`(25 coordinators,
hand-edited canonical, `apiforge agents sync` renders `.claude/agents`,
`.agents/agents`, `.codex/agents` mirrors); skills `.claude/`(14),
`.agents/`(14), `.devin/`(15), `.github/`(14). `cli_install_pretty.py` =
interactive UX. `forge.json` + `forge.agentic.json` present.

### 2.6 platform-forge

`platformforge/install/service.py` (421 lines) over vendored `_installkit.py`;
`mcp_command=("platformforge-mcp",)`, `mcp_verify_tool="platformforge_inspect"`,
`render_assets=None` — install writes managed MCP key + markers only (the
committed `.claude/agents`(41)/`.agents/agents`(41)/`.codex/agents`(41)/
`.devin/`(41+12 skills) mirrors are repo-dev assets, not shipped install
assets). `forge.json` + `forge.agentic.json` present.

### 2.7 forge-doctor-api

`src/forge_doctor_api/install/service.py` (352 lines) — ForgeSpec with
`mcp_command=("forge-doctor-api","mcp")`,
`mcp_verify_tool="doctor.get_reliability"`, `render_assets=lambda ctx: {}`
(no host mirrors published — installs MCP key + marker blocks only);
`spawn_ok=True` (install lifecycle only; scan path keeps the no-subprocess
boundary). Checkout adapter `scripts/forge_install.py` (used by forge-cli
`nativeInstall` as `{python} scripts/forge_install.py install` — precedent
for packages that can't host the engine); `scripts/forge_hosts.py` =
checkout-level host observe/launch kept out of `src/` by package boundary.
`forge.json` (has `install_command` template + `lab` block) +
`forge.agentic.json` (2 workflows: scan, diagnose). `.claude/agents/` has 1
file (dev-only). MCP servers in `handoff/mcp_server.py`,
`integrations/`.

### 2.8 forge-doctor-data

`src/forge_doctor_data/install/service.py` — same contract shape,
`mcp_verify_tool="get_execution_baseline"`, `_render_for` returns `{}`
(comment: "No repo-authored host mirrors exist today"). `forge.json` +
`forge.agentic.json` present. Vendored scripts. No host asset dirs.

### 2.9 forge-portal / forge-lens

- `forge-portal`: Angular app (`angular.json`, `portal_core`, `e2e/`). In
  forge-cli `FORGE_REPOS` as `kind:'node'` with `verify=npx ng version` and
  **no** `nativeInstall`. No `forge.json`, no installer machinery, no host
  assets. `docs/installation/` exists (usage docs). Not a parity source for
  the install engine.
- `forge-lens`: only `prompt_evo_inicial.md` — not yet a forge; nothing to
  audit.

### 2.10 data-sentinel — current state at HEAD

- **Exists**: `src/data_sentinel/installation/` (uncommitted ds-0109 work):
  `contracts.py` (`InstallScope/InstallProfile/GatewayProfile/ComponentKind`
  incl. `HOST_CONFIG`,`MARKERS`,`PORTAL_LAUNCHER`; `InstallChange`,
  `ManagedFile`, `SourceInfo`, `InstallPlan` w/ deterministic `plan_id` =
  sha256[:16] of canonical payload, `InstallReceipt`,
  `assert_no_secrets`), `planner.py` (pure `plan_installation`, merge-json
  support, REFUSE on foreign files, rollback_plan), `ownership.py`
  (`OwnershipLedger` + `sha256_file`, `.data-sentinel/installation-ledger.json`).
  11 tests in `tests/unit/installation/test_contracts.py`.
- **MCP**: `src/data_sentinel/mcp_server.py` — real stdio server over `mcp`
  SDK (extra `mcp>=1.9`), roots gated by `DATA_SENTINEL_MCP_ROOTS`;
  `data-sentinel mcp serve` + `python -m data_sentinel.mcp_server`.
- **CLI** (`data_sentinel.cli:app`, typer): `analyze`, `doctor` (env checks),
  `capabilities`, `agents`, `config`, `glue|spark|sql|report|lakehouse|
  import|investigate|mcp|api` groups. **No** `install`/`status`/`repair`/
  `uninstall`/`manifest` commands.
- **Agents**: `agents/specialists.py` — 18 registered specialists
  (coordinator, spark/glue/iceberg/lakeformation/sql/quality/lineage/
  security/report + EMR family) as in-code `AgentDescriptor`s; not exposed
  as host assets.
- **Packaging**: `pyproject.toml` — `name=data-sentinel`,
  `requires-python>=3.11`, script `data-sentinel`, extras
  `aws/stats/api/dev/mcp`; wheel `packages=["src/data_sentinel"]`, **no**
  `force-include` for host assets (none exist to include); sdist includes
  src/tests/schemas only. Version `0.1.0`.
- **Absent**: `forge.json`, `forge.agentic.json`, `install.sh`/`install.ps1`/
  `install.windows.sh`/`setup.sh`/`setup.ps1`, `scripts/forge_bootstrap.py`,
  `_installkit.py`, `skills/`, `agents/` asset dirs, `.claude/`, `.agents/`,
  `.codex/`, `.devin/`, `.github/agents`, `.claude-plugin/`, root
  `manifest.json`, `AGENTS.md`, `CLAUDE.md`, `.env.example` (verified: none
  at repo root; `.env` absent too), `docs/installation/` dir (single
  `docs/installation.md` instead), `~/.forge` registration, forge-cli
  catalog entries, the-forge adapter.
- Grill-gate decisions already recorded
  (`docs/cycles/cycle-08-2-grill-gate.md`, uncommitted): wheel-packaged
  assets at `src/data_sentinel/installation/assets/` + checkout fallback;
  Typer+Rich prompts; `data-sentinel manifest` machine-readable output +
  documented patch for forge-cli repo (never auto-written); curated catalog
  4-5 skills + 3 agents.
- Specs queued: `factory/specs/inbox/ds-0110..ds-0118` map 1:1 to prompt
  phases (see §3 below).

---

## 3. Gap list for Data Sentinel — ordered by prompt phases

| Phase (prompt) | Spec | Gap (vs. sibling baseline) |
|---|---|---|
| §1 Audit | ds-0109 (active) | This document. Also required by §1.3: `docs/installation/forge-parity-matrix.md` — can be generated from §1 here. |
| §2 Universal install architecture | ds-0109 | Contracts+planner+ownership exist. Missing: `discovery/` (env+host probe), `manifests/` (asset manifest + integrity), `profiles/` (profile→kinds map exists only as enum), `hosts/` adapters, `assets/` packaged catalog, `environment/` (python/venv discovery), `validation/` (post-apply checks), `repair/`, `uninstall/`, `compatibility/` (forge-cli contract surface), applier (journalled writes + backups + rollback — installkit `apply_install` equivalent), lock file, receipt store, `~/.forge/installations` registration. |
| §3 Interactive installer | ds-0110 | No `install` command at all; need typer group + `rich.Prompt`/`Confirm` interactive flow, `--scope/--root/--host/--profile/--components/--gateway-profile/--dry-run/--yes` flags, CI no-block behavior, JSON doc output mode. Collision check: `data-sentinel doctor` already exists (env doctor) vs prompt's `install doctor` — keep `install doctor` subcommand namespaced under `install` group. |
| §4 Host adapters | ds-0111 | Zero adapters. Need per-host capability matrix + writers for claude (`.claude/skills`,`agents`,`~/.claude.json` or project `.mcp.json`), codex (`.codex/agents/*.toml`, `.agents/skills`, `~/.codex/config.toml` MCP — user scope only, register NOT_APPLICABLE at project scope like installkit does), devin (`.devin/`,`.agents/`), copilot (`.github/{skills,agents}`); cursor optional. |
| §5 Skills | ds-0112 | No skills assets exist. Need canonical `skills/` tree (or packaged assets dir per grill-gate decision) with SKILL.md files bound to real CLI verbs; then host mirrors rendered at install time. |
| §6 Agents | ds-0113 | 18 in-code specialists exist (`agents/specialists.py`); need declarative manifests (AgentDescriptor → host formats: Claude md, Codex TOML, Devin/Copilot md), agent-teams compositions, honest unsupported-host recording. |
| §7 MCP install+lifecycle | ds-0114 | Server exists (`mcp_server.py`); missing: install-time config writing (`.mcp.json` managed key / per-host config), environment-resolved command (never absolute dev paths — siblings use console-script name, not `sys.executable`, in forge.json `mcp_command`), post-install real handshake validation (installkit `mcp_verify` equivalent: initialize→tools/list→one safe tool call), `mcp_verify_tool` designation (a no-arg read-only `sentinel.*` tool). |
| §8 Python runtime & bootstrap | ds-0115 | No bootstrap: need `scripts/forge_bootstrap.py` (vendored or Sentinel-native equivalent), `install.sh`/`install.ps1`/`install.windows.sh`/`setup.*` thin wrappers, source-method detection (wheel/git/zip/dir/gitless — forge-cli's `LocalForgeSourceDetection/v1` states), python discovery (resolve `python3`/`python`/`py -3`, `requires-python` floor), isolated venv `~/.forge/installs/` + `~/.local/bin` shims, integrity manifest for assets. |
| §9 Forge CLI compat | ds-0116 | Missing `forge.json` (ForgeDescriptor/v1: `forge_id`, `package`, `distribution`, `cli`, `python`, `mcp_command`, `install_command`, extras). forge-cli changes needed (cross-repo diff, NOT auto-applied): add `data-sentinel` to `FORGE_REPOS` (nativeInstall command `['data-sentinel','install']`, flags `['scope','profile','components','host','gateway-profile']`, ops update/uninstall) + `REGISTRY_PACKAGES` (dist `data-sentinel`, bin `data-sentinel`, minPython `3.11`, `mcp`, `mcp_safe_tools`, extras `['mcp']`). PyPI publish is currently absent — registry path is future; `forge-cli install ./data-sentinel-forge` (local source) is the near-term path and needs `setup.sh`/`install.sh` or `scripts/forge_bootstrap.py` present. |
| §10 The Forge discovery | ds-0116 | Need `forge.agentic.json` (SpecialistAgenticManifest/v1: provider `data-sentinel`, cli_entry `data_sentinel.cli:app`, workflows mapping to `investigate run`/`glue diagnose`/`spark`/`sql analyze`/`capabilities`/etc., `mcp_command`, host_adapters, `read_only_default`). A the-forge provider adapter (`the-forge/adapters/<sentinel>`) would be a cross-repo change — document contract, don't implement blindly. |
| §11 Environment intelligence | ds-0117 | Missing: env discovery (OS/terminal/python/pip|uv/git/hosts/permissions/existing install — forge-cli `discovery.ts` is the reference), `.env` handling (never overwrite existing; no `.env.example` exists yet — create one), corporate-env paths (python off PATH, proxy, no-sudo, offline, restricted net, Git Bash). |
| §12 Lifecycle | ds-0117 | Missing: `install status` (ledger+drift+receipts), `install doctor` (integrity+mcp handshake+host compat), `install repair` (re-assert managed only, heal marker/mcp-key), `install update` (pinned only, never `latest`), `install uninstall` (managed-only removal, excise markers, unset mcp key, `--purge` state). Naming: `data-sentinel install status` (namespaced) vs siblings' flat `status`/`repair`/`uninstall` — pick per prompt §12 UX guidance; spark-forge-aws shows both shapes coexist (`status` top-level + `install doctor` subcommand). |
| §13 Tests/homologation | ds-0118 | Only 11 contract tests exist. Need: host-adapter fixtures, dry-run no-write proof, rollback, golden fixtures (corrupted manifest, tampered asset, partial install, user-modified managed file, mixed forges), E2E matrix A-AO, cross-platform CI. |
| §14 Security gates | cross-cutting | Ownership/adopt rules exist in planner; missing: path-traversal/symlink refusal in applier, `_forge_managed`-style namespaced writes, secret scanning on *receipt store write* (assert_no_secrets exists but nothing calls it), lock. |
| §15 Docs | ds-0118 | `docs/installation/` dir absent (24-file plan in prompt); `docs/installation.md` exists (wheel-only scope today). PT-BR. |

---

## 4. Recommended target architecture

Module map for `src/data_sentinel/installation/` (extends the ds-0109
files already on disk; names track the prompt §2 map and the installkit
concepts):

```text
src/data_sentinel/installation/
  __init__.py                 # public API (exists)
  contracts.py                # EXISTS — InstallPlan/InstallReceipt/enums
  planner.py                  # EXISTS — deterministic plan (extend: merge-json
                              #   kinds, workspace members, refusal codes)
  ownership.py                # EXISTS — OwnershipLedger (extend: managed vs
                              #   adopted actions, kind-aware drift like
                              #   installkit _entry_intact)
  discovery.py                # env + host detection: python/git/uv probes,
                              #   installed hosts (binary + config evidence,
                              #   never inference), existing install state,
                              #   source-kind classification (wheel/git/zip/
                              #   dir/gitless → LocalForgeSourceDetection-like)
  hosts/
    __init__.py               # adapter registry + HostCapabilityMatrix
    base.py                   # HostAdapter protocol: detect/plan/apply/
                              #   validate/rollback + shared merge helpers
    claude.py                 # .claude/{skills,agents}, ~/.claude.json or
                              #   project .mcp.json, plugin manifest
    codex.py                  # .codex/agents/*.toml, .agents/skills,
                              #   ~/.codex/config.toml (user-scope MCP only —
                              #   NOT_APPLICABLE at project scope)
    devin.py                  # .devin/, .agents/ shared mirror
    copilot.py                # .github/{skills,agents}
    cursor.py                 # optional; only with real homologation
  assets/
    __init__.py               # catalog API: packaged assets primary
    skills/<name>/SKILL.md    # canonical skill sources (shipped in wheel)
    agents/<name>.md|.toml    # canonical agent descriptors
    manifest.json             # asset manifest (paths+sha256) —
                              # forge/IntegrityManifest-like
  environment.py              # python discovery (python3/python/py -3,
                              # FORGE_PYTHON-style override), venv paths,
                              # requires-python check, OS/arch
  applier.py                  # journalled apply: pre-state backups,
                              # atomic writes, rollback on failure,
                              # marker-block writes, .mcp.json managed key
  receipts.py                 # receipt store under .data-sentinel/receipts/
                              # (+ ~/.forge/installations/data-sentinel.json
                              #   registration per InstallationManifest/v1)
  validation.py               # post-apply checks incl. real MCP stdio
                              #   handshake (initialize→tools/list→one
                              #   declared safe tool call)
  repair.py                   # re-assert drifted managed files only
  uninstall.py                # managed-only removal + marker excise +
                              # mcp unset + optional --purge
  lifecycle.py                # status/doctor/update orchestration
  compatibility.py            # forge.json emit/parse, forge-cli flag
                              # surface, SpecialistAgenticManifest emit
  lockfile.py                 # O_EXCL .install.lock w/ stale reclaim
scripts/
  forge_bootstrap.py          # portable bootstrap (venv+wheel+shim+
                              # register+receipt) — vendored-installkit-style
forge.json                    # ForgeDescriptor/v1
forge.agentic.json            # SpecialistAgenticManifest/v1
install.sh / install.ps1 / install.windows.sh / setup.sh / setup.ps1
pyproject.toml                # + force-include of installation/assets into
                              #   wheel (siblings' proven pattern)
docs/installation/            # §15 doc set
```

Honest scope note: the prompt's §2 sketch (`contracts/`, `manifests/`,
`discovery/`, `planner/`, `profiles/`, `hosts/`, `assets/`, `environment/`,
`ownership/`, `receipts/`, `validation/`, `repair/`, `uninstall/`,
`compatibility/`) is a *conceptual* map — the existing flat files
(`contracts.py`, `planner.py`, `ownership.py`) already landed and work;
keep them flat modules rather than refractoring into subpackages unless
size demands it.

**Vendoring decision point**: all six Python siblings vendor the identical
`forge_installkit.py` (1732 lines, stdlib-only, `_SOURCE_SHA256`
`bc189dd2ae0028ce`, canonical at `the-forge/scripts/installkit/`). Two
options for Sentinel: (a) vendor `_installkit.py` like every sibling —
instant parity of ledger/lock/markers/mcp/repair/uninstall/handshake, but
duplicates the engine in a repo whose `installation/` contracts are
pydantic-typed and already divergent; (b) implement a Sentinel-native
engine honoring the same `forge/*` document schemas (the grill gate +
existing pydantic contracts imply this). Either way the *on-disk contract*
(documents, refusal codes, `~/.forge` registry, `forge.json`) must match —
that's what forge-cli and the-forge actually consume.

---

## 5. Best reference implementation

- **Primary reference — spark-forge-aws**: most complete per-forge stack
  (`install/cli.py` UX incl. interactive approve + JSON docs, `install/hosts.py`
  project-scope host table, `integrate/` user-scope machinery, 60 skills +
  14+5 agents with four host mirrors, `mcp verify`, gateway profiles,
  wheel `force-include` of assets, honest codex NOT_APPLICABLE check).
- **Contract/engine reference — the-forge**: canonical InstallKit +
  bootstrap + vendor tooling + `install auto` delegation + provider
  registration + AgentSpec/v1 (`agentic/agents/*.toml`).
- **Orchestrator reference — forge-cli**: what an installable forge must
  expose (`forge.json`, `install_command`, nativeInstall flags,
  `mcp_safe_tools`, LocalForgeSourceDetection states, registry catalog
  fields).
- **Minimal-shape reference — forge-doctor-data/api**: the slimmest valid
  sibling (engine + MCP key + markers, no host mirrors) — useful floor for
  a first Sentinel `install` before skills/agents land.
