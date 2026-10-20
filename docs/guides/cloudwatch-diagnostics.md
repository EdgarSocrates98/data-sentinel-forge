# Guia — CloudWatch Diagnostics

Diagnóstico de logs CloudWatch de jobs Glue/Spark: coleta paginada e
limitada, parsing estruturado (timestamps, níveis, exceções encadeadas,
números de linha), correlação de erros e timeline ordenada por timestamps
**observados** — nunca inventados.

## Instalação

```bash
pip install 'data-sentinel[aws]'   # traz boto3/botocore
```

O núcleo funciona sem o extra — só os conectores AWS o exigem
(`aws.boto3_ausente` orienta a instalação).

## Permissões IAM mínimas

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "SentinelCloudWatchReadOnly",
    "Effect": "Allow",
    "Action": [
      "logs:GetLogEvents",
      "logs:FilterLogEvents",
      "logs:DescribeLogStreams"
    ],
    "Resource": "*"
  }]
}
```

`ALLOWED_ACTIONS` do conector contém exatamente essas operações. Custos:
`GetLogEvents`/`FilterLogEvents` são cobradas por GB varrido em alguns
cenários — o conector limita páginas (`limit`, `max_events`) e janelas de
tempo (`start_time`/`end_time`) justamente para evitar varreduras amplas.

## Uso

O diagnóstico CloudWatch acontece dentro do fluxo Glue
(`data-sentinel glue diagnose`) ou analisando artefatos de log já
exportados via `analyze --file`/`spark explain`. Não existe comando
"fetch logs" isolado — a coleta é um passo do diagnóstico, não um dump.

```bash
# diagnóstico completo de uma run: metadados + logs + correlação + timeline
data-sentinel glue diagnose --job meu-job --run-id jr_abc123 --region us-east-1

# com profile/SSO
data-sentinel glue diagnose --job meu-job --run-id jr_abc123 \
  --profile prod-readonly --region us-east-1
```

## O que o analyzer produz

- **Eventos estruturados**: timestamp UTC-aware, nível, logger, mensagem.
  Linhas sem timestamp não recebem data inventada — entram na timeline
  apenas eventos com data observada.
- **Exceções**: classe, mensagem, frames de stack, `Caused by` encadeadas,
  linha de origem. A exceção primária é distinguida das causas.
- **Correlação**: agrupa falhas relacionadas (ex.: `ExecutorLostFailure`
  precedido por OOM) em vez de listar erros isolados.
- **Timeline**: sequência temporal para responder "o que aconteceu
  primeiro" — decisivo para causa-raiz vs sintoma.

## Interpretação do relatório

- `CONFIRMED`: assinatura inequívoca (ex.: `OutOfMemoryError` literal).
- `PROBABLE`/`POSSIBLE`: padrão compatível, falta corroboração.
- `UNKNOWN`: evidência insuficiente — o relatório diz **o que ajudaria**
  (mais janela de logs, métricas, event log Spark).
- `limitações`: o que o analyzer não conseguiu ver (janela cortada,
  grupo de log ausente, run sem eventos).

## Problemas comuns

| Sintoma | Causa provável | Ação |
|---|---|---|
| `aws.sem_credenciais` | nenhuma credencial na cadeia | `--profile`, env vars, `aws sso login`, IAM role |
| `aws.regiao_ausente` | região não resolvida | `--region` ou `AWS_DEFAULT_REGION` |
| `aws.acesso_negado` | IAM sem `logs:*` de leitura | aplicar política mínima acima |
| `aws.throttling` | muitas chamadas | o conector já limita; reduza concorrência/janela |
| timeline vazia | eventos sem timestamp | normal — só entram linhas datadas |
| `aws.offline` | perfil `offline` ativo | artefatos locais: `analyze --file` |

## Como suprir evidência adicional

Exporte eventos (console/CLI) para um arquivo local e analise offline —
o parser de log é o mesmo:

```bash
aws logs get-log-events --log-group-name /aws-glue/jobs/output \
  --log-stream-name <stream> > run.log
data-sentinel analyze --file run.log --platform aws_glue
```

## Segurança

- Mensagens de log passam pelo redator de segredos antes de qualquer
  saída ou persistência (`password=`, `AKIA…`, `Authorization:` etc.).
- Perfil `offline` (`allow_network=false`) recusa instanciar o conector.
- Nenhuma chamada mutadora existe no conector — nem como parâmetro.
