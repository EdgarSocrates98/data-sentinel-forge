# Compatibilidade com Forge CLI

Manifestos de descoberta na raiz do repo/pacote:

- `forge.json` — descriptor neutro (id, cli, python, version)
- `forge.agentic.json` — `forge/SpecialistAgenticManifest/v1`
  (workflows `analyze`/`spark-explain`/`capabilities`, read-only)

Registro manual: `docs/integrations/forge-cli-registration.md`.
Emitir programaticamente: `data-sentinel install manifest` /
`--agentic`. O Sentinel **não depende** do forge-cli — é só descoberta.
