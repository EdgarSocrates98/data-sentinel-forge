# Instalação portátil

A wheel `data-sentinel` é Python puro — sem binários nativos.
Todos os assets agentic (5 skills, 3 agents, manifestos) viajam dentro
da wheel em `data_sentinel/installation/assets/`, fixados por
`MANIFEST.sha256` (catálogo adulterado → `FORGE-INSTALL-VERIFY-FAILED`).

Funciona a partir de: wheel, checkout de repo, árvore copiada (sem
`.git`), ou `pip install -e .` (editable). `data-sentinel install env`
reporta o método detectado honestamente (`source.method`).
