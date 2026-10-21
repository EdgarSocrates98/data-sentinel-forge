---
name: data-sentinel-investigate
description: "Use quando a pergunta for 'por que meu job falhou / está lento / custa caro' e a investigação precisar ir do artefato ao relatório: descobrir capacidades (`data-sentinel capabilities`), escolher o verbo certo por tipo de artefato (log, plano, SQL, export de metadados), rodar a investigação orquestrada (`data-sentinel investigate run`) ou a análise direta (`data-sentinel analyze`, `data-sentinel glue inspect|runs|diagnose`) e fechar com `data-sentinel report show`. Use também quando não souber qual especialista responde — `data-sentinel agents` e `data-sentinel tools` listam o registry real antes de montar os pares tool:arquivo."
---

# Data Sentinel — Investigate

Orquestra a investigação ponta a ponta: do artefato ao relatório com
evidência. O motor é determinístico — achado sem `evidence_ids` não vira
`CONFIRMED`, e limitação declarada nunca vira silêncio. Esta skill decide
**qual verbo roda em qual artefato**; o diagnóstico de domínio fica nas
skills especializadas (`data-sentinel-spark-plan`, `data-sentinel-sql-review`,
`data-sentinel-quality-drift`).

## Quando usar

- O problema chega como descrição ("job Glue falhou de noite",
  "pipeline lento depois da última mudança") e há artefatos soltos —
  logs, `explain`, `.sql`, exports.
- Você precisa de um `InvestigationReport` que roteia especialistas por
  keyword determinística, executa as tools locais e valida os findings
  com o validador independente.

## Quando NÃO usar

- O artefato já está identificado e é de um domínio só: plano físico →
  `data-sentinel-spark-plan`; `.sql` → `data-sentinel-sql-review`;
  contrato/export de qualidade → `data-sentinel-quality-drift`. Ir direto
  na skill do domínio custa menos contexto.
- Você quer só re-renderizar um relatório existente → `data-sentinel-report`.

## Procedimento

1. **Descubra o que existe de verdade.** `data-sentinel capabilities`
   (`--descriptors` para CapabilityDescriptor) mostra o que os analyzers
   declaram; `data-sentinel agents` lista os especialistas do registry
   (coordinator, spark-expert, glue-expert, sql-expert, iceberg-expert,
   quality-expert, lineage-expert, root-cause-analyst, evidence-validator,
   report-specialist e a família emr-*); `data-sentinel tools` lista os
   `tool_id` aceitos no `--file` do `investigate run`.
2. **Mapeie artefato → tool.** Cada `--file` do `investigate run` é um
   par `tool_id:caminho`, repetível:

   ```bash
   data-sentinel investigate run \
     --problem "job Glue falhando com OOM no driver" \
     --file sentinel.cloudwatch.analyze_logs:driver.log \
     --file sentinel.spark.analyze_plan:plan.txt \
     --file sentinel.glue.diagnose_run:jobrun.json
   ```

   O roteamento de especialistas sai da descrição (`--problem`), então
   escreva os termos do domínio ("spark", "glue", "iceberg", "quality",
   "emr serverless", "sql"). Tool sem implementação para o input
   recebido volta como erro dentro de `limitations` — não silencia.
3. **Ou vá direto no artifact.** Sem roteamento: `data-sentinel analyze
   --file <log>` cobre logs genéricos; `analyze --sql <q.sql>` cobre SQL.
4. **Glue ao vivo é caminho separado e opcional.** Com o extra `aws` e
   credenciais: `data-sentinel glue inspect --job <j>` (metadados),
   `glue runs --job <j>` (histórico), `glue diagnose --job <j>
   [--run-id] [--dry-run]` (coleta CloudWatch + orquestra). `--dry-run`
   mostra o que seria coletado sem chamar AWS. Sem credenciais, os
   exports locais cobrem o mesmo diagnóstico offline.
5. **Feche com o relatório.** Todo analyze persiste o relatório
   versionado (salvo `--no-persist`); `data-sentinel report show --id
   <report_id>` re-renderiza, `--file` lê um JSON exportado. Leia
   `summary`, `limitations` e os `status` dos findings antes de
   apresentar.

## Contrato de evidência

- `status` do finding ∈ `CONFIRMED | PROBABLE | POSSIBLE | UNKNOWN`;
  resultado fraco **fica** fraco — nunca promova por conveniência.
- Todo finding carrega `evidence_ids`; a evidência é sanitizada (segredos
  redigidos) antes de persistir.
- `limitations` listam o que não deu para concluir — reporte-as com o
  mesmo peso dos findings. "Sem achado" onde não houve coleta é fraude:
  diga que o artefato não existia.
- O validador independente (`context.validation`) e o RCA
  (`hypotheses_supported`, `conclusions`) fazem parte da saída de
  `investigate run` — cite-os, não os reinvente.

## Limitações

- `glue *` exige o extra `aws` e credenciais; o restante é offline por
  padrão. `serve` e `mcp serve` exigem os extras `api`/`mcp`.
- `investigate run` roda só tools locais (`LOCAL_READ`): não sobe à AWS
  e não executa SQL — cada `--file` alimenta a tool com `{"file": path}`,
  então tools que pedem outros campos (ex.: `sentinel.quality.
  detect_drift` com `baseline_file`/`current_file`) não são acionáveis
  por este comando; elas valem pelo MCP (`data-sentinel mcp serve`).

Esta skill **não é despachável** (`subagent` ausente no espelho
`.agents/skills/`): ela dirige o loop e a orquestração fica no agente
pai — subagente não gera subagente por default.
