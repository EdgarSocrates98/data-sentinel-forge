# Domain Boundaries — Doctor × Sentinel × Forge

Derivado da auditoria de código (`docs/audits/doctor-sentinel-audit.md`,
SHAs: sentinel `7510b75`, doctor-data `266e789a`, doctor-api `8912f3b2`).

## Princípio

Cada ferramenta é excelente na sua responsabilidade. Overlap de DOMÍNIO
(Glue, Iceberg, LF…) é esperado e legítimo — o que difere é o TIPO DE
EVIDÊNCIA e o PROPÓSITO:

| | Forge Doctor Data | Data Sentinel |
|---|---|---|
| Evidência primária | STATIC / CONFIG (código, IaC, configs do projeto) | OBSERVED / DECLARED (telemetria, logs, métricas, planos, metadados de catálogo) |
| Momento | antes/durante desenvolvimento e CI | runtime / pós-falha / investigação |
| Pergunta | "o projeto está correto/saudável?" | "por que a execução falhou/degradou?" |
| Saída | checks com fingerprint, remediation, baseline | findings + evidence graph + timeline |

## Responsabilidades primárias

### Doctor-owned (não duplicar no Sentinel)
- Auditoria de projeto/repo: REP/PY/DEP/GIT/CI/DOCKER/AWS-CLI hygiene.
- Detecção estática de padrões em código e IaC (GLUE/ICE/LF/TF/PARQ ids).
- Baseline/histórico de findings (`history`, `drift`, supressões).
- Platform entity graph estático, remediation plans, policy packs.
- Catálogo de versões/EOL de runtimes como fatos de conhecimento estático.

### Sentinel-owned (não duplicar no Doctor)
- Coleta e correlação de telemetria operacional (CloudWatch logs/metrics).
- Análise de planos de execução Spark (EXPLAIN/AQE), join/shuffle/skew em
  runtime, config advisor orientado a evidência de execução.
- Diagnóstico de falha: OOM, skew, executor lost, fetch-failed — com
  timeline, evidence graph e vínculos justificáveis entre fontes.
- Avaliação operacional de IAM policy (offline evaluator) no contexto de
  um incidente — hipóteses com incerteza explícita.
- Compat runtime×formato×operação como decisão de execução (glue×iceberg
  ×op) — apoiada em knowledge rules versionadas.
- Import de bundles externos (Doctor) preservando proveniência.

### Overlap justificado (manter ambos, classificar evidência)
- **Glue runtime/Iceberg compat**: Doctor audita o projeto; Sentinel
  decide se a operação é suportada na execução concreta.
- **Lake Formation/FGAC**: Doctor verifica configuração declarativa;
  Sentinel avalia se uma falha de acesso é explicada por permissões.
- **MERGE/SQL**: Doctor detecta antipadrões em arquivos; Sentinel avalia
  riscos de execução (dup keys, idempotência, commit conflicts).
- **Capability matrices**: ambos mantêm matrizes; o conhecimento é
  convergente mas o consumo difere (auditoria vs diagnóstico).
  → candidato a knowledge-pack compartilhado (avaliar em ds-0036).

### Doctor-API
Escopo API-architecture — sem sobreposição de checks com o Sentinel.
É produtor de bundles no mesmo contrato; integração = mesmo adapter.

## Regras de ouro

1. O Sentinel NÃO audita código-fonte/projeto como produto — isso é Doctor.
   Pode analisar SQL/plano fornecido como evidência de execução.
2. O Doctor NÃO coleta nem correlaciona telemetria operacional.
3. Achados importados mantêm proveniência — nunca viram runtime-observed.
4. Nenhum dos dois executa operações cloud mutáveis.
5. Integração é opcional: cada um funciona offline e sozinho.

## Realocações futuras (backlog — nada removido agora)

- R1: avaliar knowledge pack compartilhado para fatos de versão/compat
  (glue runtime, iceberg spec) — ds-0036 decide.
- R2: Sentinel `capabilities` pode consumir Doctor capability-report como
  entrada externa (adapter), sem mudar fonte de verdade.
- R3: findings Doctor sobre IAM IaC podem alimentar hipóteses do
  avaliador IAM do Sentinel como evidência importada.
