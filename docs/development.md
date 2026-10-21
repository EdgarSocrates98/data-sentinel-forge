# Desenvolvimento

## Setup

```bash
uv sync          # venv + deps dev (ruff, mypy, pytest, pytest-cov, jsonschema)
uv run pytest    # 1025 testes
```

## Qualidade

```bash
uv run ruff check src tests          # lint (+ regras S de segurança)
uv run ruff format --check src tests # formatação
uv run mypy src                      # strict
uv run pytest -q
uv run pytest --cov=data_sentinel --cov-report=term-missing -q
```

Suite atual: **1025 testes, 84% de cobertura** (saída real em
[evidence/coverage.txt](evidence/coverage.txt) — `pytest --cov` sobre a
suíte completa, ~31min).

## Layout de testes

```text
tests/unit/          # contratos, config, store, analyzers
tests/contract/      # validação dos JSON Schemas exportados
tests/integration/   # CLI via CliRunner (happy path + hostis)
tests/security/      # traversal, redação, sanitização
fixtures/logs/       # logs sintéticos realistas (um por padrão)
fixtures/sql/        # queries por check + clean + broken
```

## Exportar schemas

```bash
uv run python scripts/export_schemas.py   # regenera schemas/*.schema.json
```

Teste de contrato valida que os schemas exportados correspondem aos modelos.

## Fluxo Loop Factory

Specs vivem em `factory/specs/{inbox,active,archive}`. Prompts, runs e
reviews em `factory/{prompts,runs,reviews}` são trilha de auditoria — o spec é
a fonte de verdade. Comandos:

```bash
loop-factory scan
loop-factory dispatch --agent claude --limit 1 --stage
loop-factory archive <id> --accepted
```

## Convenções

- Código e commits em inglês; docs e mensagens de usuário em PT-BR.
- Erros de domínio sempre `SentinelError(code, message, details)`.
- Nenhuma dependência nova sem ADR/spec (ver
  [ADR 0007](adr/0007-dependency-policy.md)).
- Achados novos precisam de fixture + teste — nada de detecção sem evidência
  reproduzível.

## CI

`.github/workflows/ci.yml`: matrix Ubuntu/Windows/macOS × Python 3.11/3.12 —
lint, typecheck, testes.
