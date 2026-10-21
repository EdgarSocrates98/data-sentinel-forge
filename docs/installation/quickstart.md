# Quickstart — instalação agentic

Instala o Data Sentinel no host/agente do seu projeto em um comando.

## Instalar

```bash
pip install data-sentinel-forge
cd meu-projeto
data-sentinel install          # interativo (pergunta profile/hosts)
```

Não-interativo:

```bash
data-sentinel install --yes --profile recommended --host all
```

## Verificar

```bash
data-sentinel install status   # instalações + drift
data-sentinel install doctor   # runtime, MCP handshake, assets
```

## Desinstalar

```bash
data-sentinel install uninstall        # remove só arquivos gerenciados
data-sentinel install uninstall --purge  # também remove .data-sentinel/install
```

Próximos passos: `profiles.md`, `components.md`, guia do seu host
(`claude-code.md`, `devin-cli.md`, `codex-cli.md`, `copilot-cli.md`).
