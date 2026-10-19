# Instalação

## Requisitos

- Python **≥ 3.11** (desenvolvimento testado em 3.12; CI cobre 3.11 e 3.12 em
  Linux, Windows e macOS).
- Nenhuma credencial cloud ou acesso de rede é necessário — o produto opera
  100% offline sobre artefatos locais.

## Com uv (recomendado)

```bash
git clone <repo> && cd data-sentinel-forge
uv sync                          # cria venv e instala deps (dev incluídas)
uv run data-sentinel --help
uv run data-sentinel doctor      # verifica a instalação
```

## Com pip

```bash
python -m venv .venv && source .venv/bin/activate
pip install .                    # runtime: pydantic, typer, sqlglot
data-sentinel --help
```

Para desenvolvimento com pip: `pip install -e ".[dev]"`.

## Verificação rápida

```bash
data-sentinel version     # imprime a versão instalada
data-sentinel doctor      # checks PASS/WARN/FAIL com dicas de remediação
```

`doctor` retorna `0` quando tudo passa e `1` quando existe `FAIL` — cada linha
FAIL vem com dica de remediação. Exemplo de saída real em
[evidence/doctor.txt](evidence/doctor.txt).

## Dependências de runtime

Apenas três (ver [ADR 0007](adr/0007-dependency-policy.md)):

- `pydantic` — contratos públicos e validação de configuração
- `typer` — CLI
- `sqlglot` — parsing estático de SQL

Integrações futuras (boto3, fastapi) serão **extras opcionais**, nunca
requisito do núcleo.
