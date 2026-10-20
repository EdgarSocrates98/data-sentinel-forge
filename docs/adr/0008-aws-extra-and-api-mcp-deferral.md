# ADR 0008 — boto3 como extra `[aws]`; API/MCP adiados para contratos + readiness

**Status:** accepted
**Data:** Cycle 02 (ds-0010, decisões do grill gate)

## Contexto

O Cycle 02 exige conectores AWS (Glue, CloudWatch), mas também exige que a
análise local funcione sem credenciais nem rede. §9.3/§9.4 do
`prompt_evo_cycle2.md` permitem adiar API/MCP se sua implementação completa
não for justificável neste ciclo.

## Decisão

- `boto3` entra apenas como extra opcional `[aws]` (já declarado em
  `pyproject.toml` desde o ds-0001). O núcleo permanece instalável e 100%
  funcional sem boto3; importar o conector sem o extra gera
  `ConfigurationError` com instrução de instalação.
- API e MCP **não** ganham servidor neste ciclo: entregamos contratos de
  ferramentas e testes de prontidão (ds-0017). Um servidor real entra quando
  houver consumidor — provavelmente Cycle 05/06.
- Testes AWS reais ficam atrás de `DATA_SENTINEL_AWS_TESTS=1`, skipped por
  padrão; homologação declara "validado com mocks".

## Consequências

- `pip install data-sentinel` continua com 3 deps de runtime (ADR 0007).
- Comandos `glue`/`cloudwatch` falham com hint claro sem `[aws]` — nunca
  crash.
- O relatório final não poderá afirmar validação contra AWS real — a
  restrição fica explícita por decisão, não por omissão.
