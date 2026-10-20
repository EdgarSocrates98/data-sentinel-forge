# Cycle 02 — Implementação

Registro do que foi construído, spec a spec, com decisões e correções
encontradas no caminho. Evidência por spec em
`factory/runs/ds-00XX.verification.log`.

## ds-0010 — Auditoria + baseline + scaffolding

- Auditoria real do Cycle 01 (clean venv, 168 testes na época) —
  `docs/cycles/cycle-02-baseline.md`.
- Gap corrigido: `uv sync` puro não instalava dev-deps (estavam só como
  `[project.optional-dependencies] dev`) → adicionado
  `[dependency-groups] dev`.
- Aditivos de contrato: `SourceType.{SPARK_PLAN,GLUE_JOB,CLOUDWATCH_LOG}`,
  `AnalysisResult.duration_ms`, pacote `reporting/`.
- ADR 0008 (boto3 extra + API/MCP deferral), ADR 0009 (forma do connector).

## ds-0011 — Glue connector read-only

- `connectors/aws/`: `sessions.py` (`require_boto3`, cadeia de
  credenciais SDK, recusa offline), `glue.py` (`ALLOWED_ACTIONS` =
  GetJob/GetJobs/GetJobRun/GetJobRuns, paginação `MaxResults≤50`,
  cancelamento por página **e por run**), `errors.py` (códigos PT-BR),
  `models.py` (job/run internos, args sanitizados).
- 16 testes Stubber: allowlist, paginação, cancelamento, IAM errors,
  sanitização de `DefaultArguments`.
- Fix de teste: `MaxResults` errado no stub; cancelamento não checava por
  run — corrigido no conector.

## ds-0012 — CloudWatch diagnostics

- `connectors/aws/cloudwatch_logs.py`: GetLogEvents/FilterLogEvents/
  DescribeLogStreams com janela de tempo e limite de eventos.
- `analyzers/cloudwatch/log_parser.py`: timestamps → UTC-aware, níveis,
  exceções (classe+mensagem+stack+Caused by), spans de linha.
- `diagnostics/correlation.py` + `diagnostics/timeline.py` — só entram
  na timeline eventos com timestamp observado.
- `CloudWatchLogAnalyzer` registrado (reusa padrões do log analyzer).
- Fixes: `Evidence` sem `line_no` (é `source_location`); `AnalysisResult`
  frozen → `dataclasses.replace`; exceção encadeada sem primária não é
  mais dropada; manifest shape corrigido.

## ds-0013 — Spark plan analyzer

- `analyzers/spark/plans/`: models (árvore, AQE, spans), parser tolerante
  (markers `+-`/`:-`/`|`, stage tags `*(N)`, formatos df.explain/COST/
  FORMATTED/EXTENDED), analyzer (joins, exchanges, scans, cartesian
  CONFIRMED, unknown ops preservados).
- Fixes: parsing de prefixo/stage-tag reescrito; `FindingCategory`
  mapeado para `SQL_ANTIPATTERN`/`COST` (não existe `PERFORMANCE`).

## ds-0014 — Join intelligence

- `analyzers/spark/joins/`: extractor AST (INNER/LEFT/RIGHT/FULL/CROSS/
  SEMI/ANTI, multi-chave, expressão, desigualdade), `load_stats`
  → (tables, runtime, warnings), analyzer com unicidade declarada,
  risco m2m, skew suspeito vs observado, deduplicação nunca automática.
- Fixtures: `fixtures/joins/` (SQL + descritores stats, volumes 230M+
  declarados).
- Fix posterior (achado na homologação): lado esquerdo de join encadeado
  virava `SELECT …` truncado — agora resolve o FROM real ("orders") ou
  rotula "junção-anterior"; `ANALYZE TABLE` só para identificadores reais.

## ds-0015 — SQL analyzer evolution (v0.2.0)

- Metadados estruturados (tabelas, aliases, CTEs ≠ tabelas, grafo de
  joins, predicados, subqueries, cláusulas) via `from_` do AST.
- `SELECT *` contextual: não acusa em `EXISTS`/`COUNT`/wrappers.
- Dialetos explícitos spark|trino (Athena=trino registrado, não "spark").
- `SEMANTIC_CHECKLIST` documentada (schema, tipos, NULL, duplicatas,
  cardinalidade, ordenação, regras) — AST não prova equivalência.
- Seletividade com stats declaradas.

## ds-0016 — Spark config advisor

- `analyzers/spark/config/`: `matrix.py` (11 propriedades, mínimo de
  runtime por engine/versão), `advisor.py` (target, observed, evidence,
  reasoning, experiment, benefit-hypothesis, risks, validation, rollback;
  custo/disponibilidade em recursos).
- Contexto via `ExecutionContext.extra["workload_*"]` — sem imports
  entre analyzers.

## ds-0017 — Orquestrador + CLI + reporting + API/MCP contracts

- `diagnostics/orchestrator.py`: executa analyzers por source type,
  `duration_ms` real, falhas → limitações, agrega `recommendations`
  (campo aditivo em `DiagnosticReport`).
- `reporting/render.py`: terminal/JSON/Markdown (sumário executivo,
  contexto, findings+evidência, recomendações, validações, limitações,
  versões de analyzer).
- `api/contracts.py`: shapes request/response + teste de readiness —
  sem servidor.
- CLI: grupos `glue{inspect,runs,diagnose}`, `spark{explain,optimize}`,
  `sql{analyze}`, `report{show}`; legado `analyze`/`report --input`
  preservado (callback de grupo com alias).
- Fixes: `CliRunner(mix_stderr)` inexistente; `LogEvent` é dataclass;
  falhas de analyzer agora viram limitações.

## ds-0018 — Golden + segurança + benchmarks + E2E

- `tests/golden/test_golden.py`: 20 manifestos (expected/prohibited
  findings, evidência, limitações) — 20/20.
- `tests/security/test_security_cycle2.py`: payloads hostis em plano/SQL/
  stats/AWS params — **achou um bug real**: `_STAT_KV` quadrático em
  linhas gigantes (~330s em 200KB) → bound `{1,200}` + scan prefix 8KB.
- `tests/benchmarks/test_benchmarks.py`: números reais com metadados de
  máquina → `docs/evidence/benchmarks.json`.
- `tests/e2e/test_scenarios.py`: A (4 joins→relatório), B (plano→árvore/
  limitações), C (Glue falha mockada→timeline/exceção/diagnóstico),
  D (evidência ausente→inconclusivo+"o que ajudaria"), E (alto volume→
  risco m2m). 1 teste AWS real env-gated (skip por padrão).
- Fix: labels de join e passos de validação (ver ds-0014).

## ds-0019 — Docs + validação + relatório (este ciclo)

- `docs/guides/` (6), `docs/examples/` (3 com saídas reais),
  `docs/cycles/` (architecture/implementation/validation/final-report),
  README/cli/security/matrix atualizados, ADR 0010, evidência de
  homologação completa.

## Estado numérico

- 360 testes passando + 1 env-gated skipped (~6s suite completa).
- Cobertura 88% (2723 statements). Lint ruff limpo, mypy strict limpo
  (75 arquivos fonte).
