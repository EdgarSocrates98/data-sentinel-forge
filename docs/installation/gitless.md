# Sem .git

`data-sentinel install` funciona em árvore copiada/ZIP extraído —
`install env` reporta `source.method` honestamente (`copied-tree`
vs `repo` vs `installed`). Nenhum passo exige metadados git.

A descoberta de membros de workspace também é gitless: um diretório com
`forge.json`, `forge.agentic.json`, `pyproject.toml` ou `package.json`
conta como projeto — `.git` não é exigido (ver
[workspace-installation.md](workspace-installation.md)).
