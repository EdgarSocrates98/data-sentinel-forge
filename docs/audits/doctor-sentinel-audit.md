# Auditoria comparativa — Doctor × Sentinel (Cycle 03.1, ds-0030)

Método: inspeção de código-fonte real + execução real do Doctor Data
(`forge-doctor-data` instalado em `/tmp/doctor-venv`, scan + export contra
probe project). Não baseado em README.

## SHAs

| Repo | SHA | Papel |
|---|---|---|
| data-sentinel-forge | `7510b75` | Telemetria operacional, correlação temporal, diagnósticos de workload |
| forge-doctor-data | `266e789a` | Auditoria estática de projeto/config/código data-eng (~344 checks) |
| forge-doctor-api | `8912f3b2` | Auditoria de contratos/arquitetura de APIs (OAS/gRPC/GraphQL) |

## Inventário real

### forge-doctor-data v1.0.3
- Deps: typer, rich, packaging. Extras: sql (sqlglot), schemas, watch, lsp.
- ~45 analyzers de modelo + ~44 checks; ids GLUE001-4, SPARK001-11,
  ICE000-25, LF000-18, PARQ000-42, DELTA*, TF000-22, DEP/PY/REP/GIT/CI*,
  AWS001-4 (higiene CLI apenas — NÃO análise de policy).
- Knowledge packs JSON: glue/versions, iceberg/{spec,versions,compatibility},
  lakeformation/{permissions,hybrid,cross-account,errors}, delta, cost,
  performance, errors.
- Saídas: `scan -f json` (schema_version "3.0", CheckResult) + `export
  --format handoff` (contract "handoff-bundle" v1) + jsonl/sarif/html/agent
  + contracts forge-contracts/1 (Finding/Entity/Relationship/Evidence/
  Capability/UnknownFact/Plans/HandoffBundle).
- `contracts verify` valida bundles contra schemas publicados.
- Determinístico, offline, sem LLM, sem timestamp no bundle.
- ~2.515 testes, ~67 labs, ~15 corpus golden.

### forge-doctor-api v0.2.3
- Deps: typer, rich, pyyaml (+graphql extra). Domínio: APIs (OAS001-20,
  APISEC, RELAPI, GRPC, GQL, DRIFT, COMPAT001-30, CLIENT, ASYNC).
- Saídas: `scan -f json` (schema "1.0": findings+unknowns+gate),
  DoctorReport v1.0, ApiHandoffBundle (handoff_version 1|2),
  Forge Protocol v2 (envelope tipado).
- Mesma família EvidenceKind; severidades MAIÚSCULAS; Confidence inclui
  UNKNOWN (exige `unknowns`); entity_ids `kind:domain:identifier`.
- Vendored forge-contracts/1 idêntico; `HandoffBundle.from_dict` JÁ aceita
  o shape legado do doctor-data (results/graph/capabilities-map).
- ~1.314 testes. Zero overlap de checks com domínios data-eng.

### data-sentinel (baseline)
- 10 analyzers operacionais: glue/cloudwatch (logs+metrics+timeline),
  spark (plan+config), sql, iceberg (metadata), lakeformation/fgac-fta,
  crossaccount (graph), iam (S3/KMS policy eval), operations (MERGE/
  APPEND), cost, quality.
- Contratos v1.0.0 + lakehouse; 8 regras YAML; store SQLite; CLI completa.
- Evidências OBSERVED/DECLARED/STATIC_INFERRED com proveniência.

## Matriz de sobreposição

| Domínio | Doctor (static) | Sentinel (operacional) | Classificação |
|---|---|---|---|
| Glue runtime versão/EOL | GLUE002 + knowledge | regra glue-runtime-iceberg | overlap justificável — fontes e propósitos distintos |
| Iceberg metadata manutenção | ICE0xx checks estáticos | snapshot/manifest analysis | complementar |
| FGAC/Lake Formation | LF000-18 static audit | compat engine + resolver | overlap justificável |
| IAM policy S3/KMS | TF0xx IaC scan | avaliador offline de policy | complementar |
| MERGE/APPEND SQL | padrões em model files | analyzer dedicado (sqlglot AST) | complementar |
| Spark skew/shuffle | SPARK checks + labs | plan analyzer + join intel | complementar |
| Project config/repo hygiene | REP/PY/DEP/GIT/CI/AWS CLI | — | Doctor-only |
| Platform graph/entities | graph builder, entity model | cross-account permissions graph | overlap parcial |
| Capability matrix | capabilities/* packs | support status + compat | overlap semântico |
| CloudWatch/logs/metrics | — | coleta+correlação temporal | Sentinel-only |
| Telemetria/timeline/incidente | — | timeline, evidence correlation | Sentinel-only |
| API contracts (OAS/gRPC) | forge-doctor-api todo | — | Doctor-API-only |
| Histórico/baseline/drift | history snapshots | — | Doctor-only (candidato a realocação futura?) |

## Formato de intercâmbio escolhido (evidência)

- **Real output**: `export --format handoff` → `contract:"handoff-bundle"`,
  `contract_version:1` (int), `schema_version:"1.0"`, keys
  capabilities/graph/plans/project/results/schema_version/summary/tool.
  Fixture real: `fixtures/doctor-data/handoff-real-probe.json`.
- `scan -f json` → `schema_version:"3.0"`, CheckResult{check_id,title,
  severity(lower),category,message,file,line,confidence,evidence_kind,
  evidence,fingerprint,tags,docs_uri,source,fixable,is_new}.
  Fixture real: `fixtures/doctor-data/scan-real-probe.json`.
- Canônico compartilhado: `forge-contracts/1` HandoffBundle
  (`contract_version:"forge-contracts/1"`, findings/entities/relationships/
  capabilities/unknowns/plans). Fixtures copiados: `fixtures/doctor-data/*`,
  `fixtures/doctor-api/forge-contracts-1-handoff.json`.
- **Implicação (§3.3)**: o bundle de interop deve ADOTAR o vocabulário
  forge-contracts/1 — não inventar formato incompatível.

## Mismatches conhecidos (o adapter deve tratar)

1. severidades lowercase (data) vs UPPER (api) vs Severity interna.
2. `check_id`+`message` (data) vs `id`+`description` (api).
3. `contract_version` int 1 (handoff real) vs string "forge-contracts/1"
   (canônico) — aceitar ambos.
4. `fingerprint` (data) vs `entity_ids` (api) vs `source_location`.
5. data Confidence {high,medium,low} sem UNKNOWN; api tem UNKNOWN+unknowns.
6. evidence_kind data: static|config|observed_metadata|runtime|derived.

## Gaps descobertos

- Doctor não coleta telemetria temporal nem correlaciona evidências entre
  fontes operacionais — todo o eixo "operational" é Sentinel-only.
- Doctor-API tem zero checks data-eng: não é fonte de sobreposição, mas é
  produtor válido de bundles (mesmo contrato) → adapter único serve ambos.
- Doctor não executa jobs/análise de workload: findings dele são sempre
  STATIC/CONFIG-derived, nunca runtime-observed → proveniência importada
  deve refletir isso.
