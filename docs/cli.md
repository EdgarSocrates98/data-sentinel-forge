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
| `--platform, -p` | Plataforma do workload (`generic`, `spark`, `aws_glue`, `athena`, `trino`…) |
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
data-sentinel capabilities [--json] [--descriptors]
```

Emite o `CapabilityManifest` de cada analyzer registrado (operações,
plataformas, limitações declaradas). `--descriptors` emite a lista de
`CapabilityDescriptor` (interop 1.0.0) para descoberta por orquestradores.

## `import` — bundles externos (opcional)

```bash
data-sentinel import doctor-bundle -f <arquivo> [--json]
```

Importa findings de um bundle Forge Doctor (handoff-bundle@1,
forge-contracts/1 ou scan-json@3.0). Offline, sem Doctor instalado;
findings importados preservam proveniência e nunca viram CONFIRMED.

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

## `glue` — inspeção read-only de jobs AWS Glue

Requer o extra `[aws]` (`pip install '.[aws]'` (no checkout)) e credenciais
da cadeia padrão do SDK.

```bash
data-sentinel glue inspect --job <nome> [--profile P] [--region R]
data-sentinel glue runs --job <nome> --limit N [--profile P] [--region R]
data-sentinel glue diagnose --job <nome> --run-id <id> [--profile P] [--region R]
```

`inspect` mostra metadados do job com `DefaultArguments` sanitizados;
`runs` lista histórico com paginação limitada; `diagnose` roda o pipeline
completo (metadados → CloudWatch logs → correlação → timeline →
analyzers → relatório). Erros AWS viram códigos PT-BR
(`aws.sem_credenciais`, `aws.acesso_negado`, `aws.throttling`, …) — ver
[docs/guides/aws-glue-connector.md](guides/aws-glue-connector.md).

## `spark` — planos e otimização

```bash
data-sentinel spark explain --file plano.txt
data-sentinel spark optimize --sql q.sql [--stats stats.json] \
    [--config spark-defaults.conf] [--dialect spark|trino]
```

`explain` faz parse tolerante de `EXPLAIN`/`df.explain()` (árvore de
operadores, joins, exchanges, AQE, spans de evidência). `optimize` roda o
pipeline composto: SQL estático + inteligência de joins + config advisor.

## `sql` — análise estática

```bash
data-sentinel sql analyze --file query.sql --dialect spark|trino [--json]
```

AST SQLGlot — 14 checks com contexto (SELECT* sem falso positivo em
EXISTS/COUNT, joins sem predicado, non-sargável, ORDER BY global, UNION
sem ALL, COUNT DISTINCT, IN grande, scan sem filtro). Ver
[docs/guides/sql-analysis.md](guides/sql-analysis.md).

## `report show` — renderização

```bash
data-sentinel report show --id <report_id> --format terminal|markdown|json
data-sentinel report show --file relatorio.json
```

Renderers em `reporting/` — Markdown inclui sumário executivo, contexto,
findings com evidência, recomendações, validações, limitações e versões
dos analyzers. `report --input` (forma legada) continua funcionando.

## Descritor de estatísticas (`--stats`)

JSON declarado pelo usuário — nunca fabricado:

```json
{"tables": {"orders": {"row_count": 230000000,
  "keys": {"customer_id": {"distinct": 45000000}}}},
 "runtime": {"stage_12": {"task_time_p50_ms": 800, "task_time_p99_ms": 21000}}}
```

Sem ele, cardinalidade fica `UNKNOWN` e o relatório diz o que coletar —
formato completo em [docs/guides/join-intelligence.md](guides/join-intelligence.md).

## `lakehouse` (Cycle 03)

| Comando | Entrada | Função |
|---|---|---|
| `lakehouse metadata -f` | metadata.json Iceberg | snapshots, evolução, small files |
| `lakehouse access -f` | AccessContext JSON | cross-account + grafo |
| `lakehouse policy -f` | policy/envelope JSON | IAM/S3/KMS offline |
| `lakehouse operation -f` | SQL ou envelope | MERGE/APPEND/DDL (nunca executa) |
| `lakehouse compat` | flags runtime/op/mode | veredito via knowledge base |

Verbos de arquivo com `--json`, `--quiet`, `--no-persist`, `--format`,
`--output`; `lakehouse compat` aceita só `--json` + seus flags próprios.

## `serve` — Control Center API (Cycle 06)

```bash
data-sentinel serve [--host 127.0.0.1] [--port 8790] [--root <dir>]
```

Sobe a API FastAPI do Control Center via uvicorn (requer extra `api`:
`pip install '.[api]'` (no checkout)).

- `--host` default `127.0.0.1` — bind não-local emite **aviso** (a API
  expõe arquivos locais; use só em rede confiável).
- `--port` default `8790`.
- `--root` (repetível) — raízes permitidas para `files`/`file` dos
  endpoints; default = cwd do processo + `~/.cache`. Path fora das raízes
  → `403`.

Endpoints versionados em `/api/v1/*` (health, capabilities, tools, agents,
severities, investigations + SSE stream + graph, `analyze/{id}`); OpenAPI
em `/api/openapi.json`, Swagger em `/api/docs`. Investigações persistem
em SQLite (`~/.data-sentinel/sentinel.db`) e sobrevivem a restart.
Guia completo:
[docs/guides/control-center.md](guides/control-center.md).
