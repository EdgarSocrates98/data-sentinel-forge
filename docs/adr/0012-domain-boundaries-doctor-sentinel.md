# ADR 0012 — Fronteiras de domínio Doctor × Sentinel

## Status
Accepted (Cycle 03.1, ds-0031)

## Contexto
Doctor Data e Data Sentinel cobrem domínios coincidentes (Glue, Iceberg,
Lake Formation, IAM, SQL) mas com evidências e propósitos distintos — o
audit (`docs/audits/doctor-sentinel-audit.md`) mostra que o Doctor emite
findings STATIC/CONFIG sobre projeto/código, enquanto o Sentinel emite
findings sobre telemetria e execução. Sem fronteira formal, cada lado
cresce na direção do outro (duplicação de motores e falsas expectativas).

## Decisão
Fronteira por TIPO DE EVIDÊNCIA + PROPÓSITO, não por domínio:
- Doctor = auditoria estática de projeto/config/código (STATIC/CONFIG).
- Sentinel = inteligência operacional sobre execução/telemetria
  (OBSERVED/DECLARED).
- Overlap de domínio é legítimo quando os dois lados produzem classes
  diferentes de evidência para perguntas diferentes.
- Interoperabilidade via bundle versionado (forge-contracts/1), opcional,
  unidirecional (import no Sentinel neste ciclo).
- Nenhum código é removido de nenhum lado neste ciclo; realocações
  futuras passam por migration-safety checklist (ds-0036).

## Consequências
- O adapter importa findings Doctor marcando proveniência externa —
  nunca auto-CONFIRMED nem runtime-observed.
- O eixo operacional do Sentinel (grafo de evidência, timeline,
  correlação cross-source) é livre para evoluir sem medo de "pisar" no
  Doctor, pois o Doctor não tem superfície equivalente.
- Regras de conhecimento convergentes (versões Glue/Iceberg) podem virar
  knowledge pack compartilhado somente se ds-0036 demonstrar benefício.
