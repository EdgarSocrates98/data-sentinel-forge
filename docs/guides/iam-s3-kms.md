# Guia — IAM/S3/KMS

Análise **offline** de documentos de policy — nenhuma API AWS é chamada.

```bash
data-sentinel lakehouse policy -f policy.json
```

## Formatos aceitos

- Policy crua: `{"Version": "...", "Statement": [...]}`
- Envelope: `{"policies": {"identity": {...}, "boundary": {...}},
  "context": {"bucket": {...}, "kms": {...}},
  "evaluate": [{"action": "s3:GetObject", "resource": "arn:..."}]}`

## Vereditos do avaliador

- `denied`: Deny explícito cobre (ação, recurso) — CONFIRMED.
- `allowed`: Allow cobre — POSSIBLE; **não prova acesso** (boundaries,
  SCPs, resource policies, session podem negar).
- `unknown`: nada cobre — hipótese, não prova de negação.

## S3/KMS contexto

- Bucket cross-account sem policy visível → UNKNOWN.
- Chaves KMS origem ≠ destino → POSSIBLE (duas cadeias).
- `SimulatePrincipalPolicy` não é usado por padrão; limitações doc.
- Decrypt nunca é executado.
