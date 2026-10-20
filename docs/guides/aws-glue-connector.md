# Guia — AWS Glue Connector

Conector **read-only** de metadados do AWS Glue. Requer o extra `[aws]`:

```bash
pip install 'data-sentinel[aws]'
```

Sem o extra, qualquer uso do conector falha com `aws.boto3_ausente` e a
instrução acima — o núcleo nunca quebra.

## Permissões IAM mínimas (referência)

Ajuste ARNs/região ao seu ambiente. **Nada aqui é concedido
automaticamente** — copie, revise e aplique via sua esteira de IAM.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SentinelGlueReadOnly",
      "Effect": "Allow",
      "Action": [
        "glue:GetJob",
        "glue:GetJobs",
        "glue:GetJobRun",
        "glue:GetJobRuns"
      ],
      "Resource": "*"
    }
  ]
}
```

Enforcement de código: `ALLOWED_ACTIONS` no conector contém exatamente essas
4 operações — qualquer chamada fora da lista é rejeitada
(`aws.acao_nao_permitida`). `StartJobRun`, `StopJobRun`, `UpdateJob` e demais
mutações **não existem** no conector.

## Autenticação

Cadeia padrão do SDK: `--profile`, variáveis `AWS_*`, IAM role da instância,
SSO (`aws sso login`), e `AssumeRole` opcional passando o ARN (a role já deve
estar autorizada — o conector não concede nada). Região via `--region` ou
`AWS_DEFAULT_REGION`.

## Comandos CLI

```bash
# metadados read-only do job (definição, args sanitizados, defaults)
data-sentinel glue inspect --job meu-job --region us-east-1

# histórico de runs (paginação limitada por --limit)
data-sentinel glue runs --job meu-job --limit 20 --region us-east-1

# diagnóstico de uma run: metadados + CloudWatch logs + correlação + timeline
data-sentinel glue diagnose --job meu-job --run-id jr_abc123 \
  --profile prod-readonly --region us-east-1
```

Sem credenciais configuradas a CLI recusa limpo:

```text
erro: glue:get_job_run: credenciais indisponíveis — configure
profile/env/IAM role/SSO [aws.sem_credenciais]
```

Exemplo completo: [docs/examples/glue-diagnostics.md](../examples/glue-diagnostics.md).

## Erros e próximos passos

| Código | Significado | Ação |
|---|---|---|
| `aws.acesso_negado` | IAM nega a ação | revisar política acima |
| `aws.nao_encontrado` | job/run não existe | conferir nome + região |
| `aws.throttling` | limite de taxa | o conector já faz backoff; persista → reduza concorrência |
| `aws.token_expirado` | credencial temporária vencida | `aws sso login` novamente |
| `aws.sem_credenciais` | nenhuma credencial | configurar profile/env/role |
| `aws.perfil_inexistente` | profile inválido | conferir `~/.aws/config` |
| `aws.regiao_ausente` | sem região | `--region` ou `AWS_DEFAULT_REGION` |
| `aws.offline` | perfil offline | mude de perfil ou use artefatos locais |

## Segurança

- `DefaultArguments`/`Arguments` são sanitizados: chaves com
  password/secret/token/key/credential viram `«redacted:arg»`; demais valores
  passam pelo redator padrão.
- `ErrorMessage` dos runs passa pelo redator antes de qualquer saída.
- Credenciais nunca são armazenadas, exibidas ou incluídas em erros.
- Perfil `offline` (`allow_network=false`) recusa instanciar o conector.

## Custos

`GetJob*`/`GetJobRun*` não têm custo de API por chamada na AWS; ainda assim o
conector limita paginação (`limit`) para não varrer históricos enormes sem
necessidade.
