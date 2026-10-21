# forge-cli registration — data-sentinel-forge

Cycle 08.2 (§9.5): this document is the **documented patch** for registering
Data Sentinel in forge-cli. It is applied to the sibling repo only with
explicit owner approval — Sentinel never writes to another forge's tree.

## `src/constants/repos.ts` — append to `FORGE_REPOS`

```ts
{
  name: 'data-sentinel-forge',
  url: 'https://github.com/EdgarSocrates98/data-sentinel-forge',
  description: 'Diagnóstico determinístico de workloads de engenharia de dados',
  kind: 'python',
  verify: ['data-sentinel', '--help'],
  nativeInstall: {
    command: ['{bin}', 'install'],
    flags: ['scope', 'root', 'host', 'profile', 'components', 'gateway', 'yes', 'dry-run'],
    ops: {
      update: ['{bin}', 'install', 'update'],
      uninstall: ['{bin}', 'install', 'uninstall'],
      status: ['{bin}', 'install', 'status'],
    },
  },
  nextSteps: ['data-sentinel install --yes'],
},
```

## `src/registry/catalog.ts` — append to `REGISTRY_PACKAGES`

```ts
{
  name: 'data-sentinel-forge',
  dist: 'data-sentinel-forge',
  bin: 'data-sentinel',
  minPython: '3.11',
  mcp: ['{bin}', 'mcp', 'serve'],
  extras: ['mcp', 'api'],
  origin: 'official',
},
```

## Discovery contract

- `forge.json` (repo root): ForgeDescriptor — forge-cli source detection.
- `forge.agentic.json` (repo root): `forge/SpecialistAgenticManifest/v1` —
  the-forge routing manifest; all workflows `DIAGNOSTIC_ONLY` + `read_only`.
- `data-sentinel install manifest` / `--agentic`: same manifests emitted by
  the installed CLI (works from wheel/git/zip — no checkout needed).
- `~/.forge/installations/data-sentinel-forge.json`: written by
  `install` via the shared installkit registry.

## Independence guarantee (§10.4)

Zero runtime dependency on forge-cli or the-forge: `data_sentinel` imports
neither package; detection is best-effort (manifest + `~/.forge` presence).
