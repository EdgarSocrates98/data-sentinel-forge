# ADR 0009 — Forma do connector protocol AWS

**Status:** accepted
**Data:** Cycle 02 (ds-0010)

## Contexto

Conectores AWS precisam de credenciais, read-only enforcement, modelos de
retorno e tratamento de erro consistentes entre Glue e CloudWatch — sem vazar
boto3 para as camadas de análise.

## Decisão

- `connectors/aws/sessions.py`: fábrica de sessões boto3 via cadeia padrão de
  credenciais (profile/env/IAM role/SSO/AssumeRole opcional/região). Nenhum
  armazenamento próprio de credenciais.
- Cada conector declara `ALLOWED_ACTIONS` (allowlist de APIs read-only) e
  só chama membros dessa lista — teste assegura que nenhum método mutável é
  invocável pelo objeto.
- Conectores retornam **modelos internos** (dataclasses/`BaseModel` em
  `core/models` ou no próprio módulo), nunca dicts boto3 crus — a camada de
  análise não conhece boto3.
- Erros AWS mapeados para `SentinelError` com taxonomia fixa
  (access_denied, not_found, throttling, …) + hint PT-BR de próxima etapa.
- `allow_network=false` (perfil offline) bloqueia instanciação do conector.
- Campos sensíveis passam por `sanitize_evidence_excerpt` antes de sair do
  conector.

## Consequências

- Analyzers consomem artefatos uniformes — CloudWatch e arquivos locais viram
  a mesma entrada.
- Read-only é enforcement de código, não convenção.
- Testes usam Stubber do botocore — sem conta AWS.
