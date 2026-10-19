# Exemplos executáveis

Rode a partir da raiz do repositório. Todos os comandos foram executados e
produziram as saídas capturadas em `docs/evidence/`.

## 1. Diagnóstico de log Glue/Spark

```bash
data-sentinel analyze --file fixtures/logs/glue_oom.log
```

Saída real (trecho): achado `out_of_memory` `HIGH/CONFIRMED` com evidências
citando `fixtures/logs/glue_oom.log:5` e `:8`, recomendações de
`spark.driver.memory`/`spark.executor.memory` e limitações declaradas.
Arquivo completo: `docs/evidence/analyze-glue-oom.txt`.

## 2. Análise estática de SQL em JSON

```bash
data-sentinel analyze --sql fixtures/sql/join_no_predicate.sql --json --no-persist
```

Saída real em `docs/evidence/analyze-sql.json`: achados POSSIBLE para join sem
predicado + `SELECT *`, metadados da query e a limitação explícita de que
execução física não é observada.

## 3. Persistência + renderização

```bash
# persiste (default) e mostra o report_id no cabeçalho da saída
data-sentinel analyze --file fixtures/logs/mixed.log

# renderiza a partir do id
data-sentinel report --input <report_id>

# ou a partir de um arquivo exportado
data-sentinel analyze --file fixtures/logs/mixed.log -o /tmp/rel.json --no-persist
data-sentinel report --input /tmp/rel.json
```

## 4. Saúde e capacidades

```bash
data-sentinel doctor          # PASS/WARN/FAIL por check, exit 1 se FAIL
data-sentinel capabilities    # manifests dos analyzers
data-sentinel config show     # config resolvida + fontes
```

## 5. Falha segura (demonstração do path guard)

```bash
data-sentinel analyze --file ../../etc/hostname
# erro: caminho fora das raízes permitidas [security.fora_das_raizes]  (exit 1)
```
