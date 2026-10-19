# ADR 0006 — Exit-code scheme da CLI

**Status:** accepted
**Data:** Cycle 01 (ds-0008)

## Contexto

Automação e scripts precisam distinguir sucesso, erro de uso, erro de domínio e
falha interna sem parsear texto.

## Decisão

| Código | Significado |
|---|---|
| 0 | Sucesso — inclusive análise que encontra achados |
| 1 | Erro de domínio/usuário: entrada inválida, path rejeitado, config inválida, doctor com FAIL |
| 2 | Erro de uso: flags inválidas, argumentos em falta (padrão Typer) |
| 3 | Erro interno inesperado |

`--verbose` re-levanta a exceção interna (traceback) para diagnóstico; sem ele,
erros internos viram `erro interno: ...` no stderr com saída 3. Achados de
qualquer severidade NÃO mudam o código — o relatório é a saída.

## Consequências

- `analyze` retorna 0 mesmo com findings CRITICAL — quem precisa de gate por
  severidade consome `--json`.
- `doctor` retorna 1 quando há FAIL — útil como health check em CI.
