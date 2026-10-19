# Contribuindo

Obrigado pelo interesse no Data Sentinel!

## Fluxo

1. Faça fork e crie uma branch descritiva (`feat/...`, `fix/...`).
2. Todo trabalho segue o ciclo Loop Factory em `factory/specs/` — proponha ou atualize uma spec antes de mudanças grandes.
3. Garanta que `uv run ruff check src tests`, `uv run mypy src` e `uv run pytest -q` passam.
4. Abra um PR descrevendo o problema e a solução; commits pequenos e descritivos em inglês.

## Regras do projeto

- Diagnósticos sempre sustentados por evidência; nunca inventar resultados.
- Execução determinística antes de qualquer uso de LLM.
- Arquitetura independente: sem dependência obrigatória de produtos externos.
- Leitura apenas (read-only) por padrão; nunca modificar recursos de produção.
- Documentação e mensagens de CLI em PT-BR; código e commits em inglês.
