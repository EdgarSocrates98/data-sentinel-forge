# Complementaridade Doctor × Sentinel (Cycle 03.1 §7.4)

Execução REAL: forge-doctor-data 1.0.3 (venv `/tmp/doctor-venv`) +
data-sentinel in-process, 10 cenários × 3 modos.
Dados brutos: `complementarity-results.json` (status VERIFIED).

## Números

| Métrica | Valor |
|---|---|
| Cenários | 10 |
| Aplicáveis ao Doctor | 4 → detectou em 2 (s01, s03) |
| Aplicáveis ao Sentinel | 9 → sinal correto em 6 + UNKNOWN correto em 3 |
| Tempo total Doctor | 2.409s |
| Tempo total Sentinel | 0.14s |
| Chamadas externas | 0 (ambos offline) |
| União interop | 713 findings importados+gerados |
| Duplicação estimada | 5 (heurística por categoria×texto) |

## Respostas §7.4

**O que o Doctor detectou sozinho?**
- s01: higiene de projeto PySpark (REP/PY — Sentinel NOT_SUPPORTED por
  design: nenhum artefato operacional era esperado ali).
- s03: checks estáticos ICE/GLUE no projeto (mesmo cenário em que o
  Sentinel deu veredito de compat — ângulos diferentes, ambos corretos).

**O que o Sentinel detectou sozinho?**
- s02 OOM Glue, s06 riscos MERGE, s07 shuffle/skew no plano,
  s08 falha da execução — todos com evidência OBSERVED que o Doctor
  não tem superfície para produzir.

**O que melhorou na combinação?**
- s10: findings estáticos (69 do Doctor) + operacionais (3 do Sentinel)
  coexistem no mesmo incidente com proveniências distintas — o relatório
  enriquecido separa "o projeto está mal" de "a execução falhou por OOM".

**O que continuou sem resposta?**
- s05 cross-account parcial: UNKNOWN correto — nenhuma ferramenta inventa
  causa sem evidência. s09 log truncado: idem.

**Houve duplicação desnecessária?**
- Estimativa de duplicação = 5/713 (~0.7%) — baixa; ocorrências são
  categorias amplas coincidindo em texto, não o mesmo achado.

**Houve regressão?**
- Nenhuma: 526 testes do Sentinel seguem verdes; nenhum código Doctor
  foi alterado.

**Capacidades a realocar?**
- Nenhuma urgente. R2 (capabilities externas como entrada) segue no
  backlog do reuse-dedup.md.

## Incerteza declarada

- Ground truth por cenário reflete a fronteira de domínio combinada
  (ds-0031) — não é um benchmark de precisão absoluta.
- s04 (permissão LF) produziu UNKNOWN+category unknown — contado como
  UNKNOWN CORRETO (a policy simples não permite concluir), não como miss.
- Doctor não foi avaliado em cenários s02/s04-s09 por falta de superfície
  correspondente — registrado como NOT_SUPPORTED, não como falha.
