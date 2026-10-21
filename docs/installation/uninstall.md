# Desinstalação

```bash
data-sentinel install uninstall            # remove só managed
data-sentinel install uninstall --purge    # + .data-sentinel/install
```

O ledger sha256 decide o que remover — arquivos do usuário, skills
estrangeiras e servidores MCP de terceiros são preservados. Blocos
gerenciados saem de `AGENTS.md`/`CLAUDE.md`; conteúdo fora dos
marcadores permanece. `--dry-run` mostra o plano sem escrever.
