# Diagnósticos Amazon EMR

Análise read-only de artefatos EMR exportados — offline-first,
sem credenciais obrigatórias.

## Uso

```bash
# artefatos exportados (DescribeCluster/ListSteps/JSON)
data-sentinel emr analyze -f cluster.json --platform ec2
data-sentinel emr analyze -f serverless.json --platform serverless
data-sentinel emr analyze -f pods.yaml --platform eks     # kubectl -o yaml

# custo estimado (tabela estática, nunca billing)
data-sentinel emr cost --platform serverless --vcpu-hours 10

# comparação honesta entre execuções
data-sentinel emr compare --baseline a.json --current b.json

# investigação agêntica
data-sentinel investigate run -p "emr serverless job failed" \
  -f sentinel.emr.analyze_serverless:job.json
```

## Exportando artefatos (você roda, nós analisamos)

```bash
aws emr describe-cluster --cluster-id j-XXX > cluster.json
aws emr list-steps --cluster-id j-XXX >> cluster.json   # ou {"calls":{...}}
aws emr-serverless get-job-run --application-id X --job-run-id Y
kubectl get pods,events -n emr -o yaml > pods.yaml
```

## Limitações

- Sem acesso direto a YARN/K8s/EMR por padrão — tudo por artefatos.
- Custos são ESTIMADOS (tabela estática us-east-1); nunca billing real.
- Spot interruption é hipótese (POSSIBLE), nunca afirmada.
- Comparação nunca declara modalidade superior sem controle de
  workload/versão/recursos.
- AWS real: conector `EmrConnector` com allowlist read-only,
  env-gated `DATA_SENTINEL_AWS_TESTS=1`.
