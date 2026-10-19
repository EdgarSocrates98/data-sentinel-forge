# Referência da CLI

App Typer: `data_sentinel.cli:app`. Todas as mensagens são PT-BR; erros vão
para **stderr**; nenhuma pergunta interativa é feita.

## Códigos de saída

| Código | Significado |
|---|---|
| 0 | Sucesso (inclusive análise com achados) |
| 1 | Erro de domínio/usuário (entrada inválida, path rejeitado, doctor FAIL) |
| 2 | Erro de uso (flags inválidas — Typer) |
| 3 | Erro interno inesperado |

`--verbose` (flag global) re-levanta exceções para diagnóstico. Detalhes em
[ADR 0006](adr/0006-exit-code-scheme.md).

## `analyze`

```bash
data-sentinel analyze --file <log>        # log Spark/Glue/local
data-sentinel analyze --sql <arquivo>     # SQL estático (nunca executa)
```

Opções:

| Opção | Efeito |
|---|---|
| `--platform, -p` | Plataforma do workload (`generic`, `spark`, `glue`, `athena`, `trino`…) |
| `--profile` | Perfil de análise (`economy`, `balanced`, `deep`, `offline`) |
| `--dialect` | Sobrescreve dialeto SQL (ex.: `trino`) |
| `--json` | Emite o `DiagnosticReport` em JSON (stdout puro) |
| `--no-persist` | Não grava no store SQLite |
| `--output, -o` | Grava o relatório JSON num caminho |

O caminho de entrada passa pelo guard de paths: deve resolver dentro do cwd ou
de `allowed_roots` configurados — `../../etc/...` é rejeitado com erro amigável
(exit 1). Arquivos binários e acima de `max_file_bytes` também são rejeitados.

Achados vêm com evidência citada (arquivo:linha, trecho sanitizado) e status
`CONFIRMED`/`PROBABLE`/`POSSIBLE`/`UNKNOWN`. Log sem padrões conhecidos gera
UNKNOWN + limitação explicando o que ajudaria — nunca diagnóstico inventado.

## `report`

```bash
data-sentinel report --input <report_id | caminho.json> [--json]
```

Renderiza relatório em texto PT-BR (achados, severidade, evidências com
localização, recomendações, limitações) ou ecoa o JSON com `--json`.

## `doctor`

```bash
data-sentinel doctor [--json]
```

Checks: versão do Python, resolução de config, store gravável, analyzers
registrados, redação de segredos. Saída `[PASS]/[WARN]/[FAIL]` + dica; exit 1
se houver FAIL.

## `capabilities`

```bash
data-sentinel capabilities [--json]
```

Emite o `CapabilityManifest` de cada analyzer registrado (operações,
plataformas, limitações declaradas).

## `config show`

```bash
data-sentinel config show [--json]
```

Configuração resolvida com segredos redigidos e a lista de fontes
(`fontes:` — layer, caminho, aplicada/encontrada/ausente).

## `version`

```bash
data-sentinel version   # data-sentinel 0.1.0
```
