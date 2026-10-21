# Troubleshooting

| Sintoma | Causa | Ação |
|---|---|---|
| `FORGE-INSTALL-VERIFY-FAILED` | asset catalog adulterado/incompleto | reinstale a wheel; `MANIFEST.sha256` divergiu |
| `FORGE-INSTALL-HOST-UNKNOWN` | host não reconhecido | use `claude,devin,codex,copilot,cursor` ou `all` |
| `FORGE-INSTALL-PROFILE-UNKNOWN` | profile/gateway inválido | `minimal/recommended/full`; gateway `economy/balanced/deep` |
| `FORGE-INSTALL-PYTHON-INCOMPATIBLE` | Python < 3.11 | suba o interpretador; `install env` mostra o detectado |
| doctor FAIL após uninstall | estado esperado pós-remoção | `install status` confirma |
| Codex sem MCP de projeto | Codex não lê `.mcp.json` de projeto | `NOT_APPLICABLE` é o status honesto, não bug |
| `install` pede `--yes` | stdin não é TTY | `--yes` ou rode interativo |
| dry-run não escreve nada | por design | use sem `--dry-run` para aplicar |
| nada instalado para cursor | Cursor não tem adapter de catálogo | limitação declarada |
