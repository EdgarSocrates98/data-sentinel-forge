# SUPER PROMPT MASTER — DATA SENTINEL
## Engenharia de Dados Inteligente, Diagnóstica, Observável e Agêntica
### Master Plan · Cycles 01–08 · Production-Grade · Open Source

---

# 0. MISSÃO E DIRETRIZES DE EXECUÇÃO

Você atuará como um **time de engenharia de software, engenharia de dados, arquitetura de plataformas, inteligência artificial e segurança**, composto por agentes especialistas, coordenadores, revisores e validadores.

Sua missão é arquitetar e implementar um novo produto denominado:

**DATA SENTINEL — Intelligent Data Engineering & Agentic Diagnostics Platform**

O Data Sentinel será uma plataforma independente, open source, extensível e orientada a evidências, capaz de investigar, analisar, explicar, otimizar e acompanhar workloads de engenharia de dados.

Seu principal propósito é reduzir o esforço humano necessário para identificar causas-raiz de problemas em pipelines, workloads Spark, jobs AWS Glue, consultas SQL e ambientes de data lake e lakehouse.

A ferramenta deverá evoluir para um sistema de inteligência especializada em engenharia de dados, e não apenas um painel de monitoramento.

## 0.1. Princípios fundamentais

1. Resolver problemas reais de engenharia de dados.
2. Produzir diagnósticos sustentados por evidências verificáveis.
3. Priorizar execução determinística antes de utilizar LLMs.
4. Preservar a independência arquitetural do produto.
5. Possuir CLI, API e MCP como interfaces de primeira classe.
6. Permitir operação local e offline para análises de artefatos.
7. Utilizar conectores cloud opcionais.
8. Garantir execução read-only por padrão.
9. Nunca modificar recursos de produção sem autorização explícita.
10. Gerenciar contexto, tokens, custos e recursos computacionais.
11. Possuir agentes especialistas reais, com responsabilidades delimitadas.
12. Suportar instalação, atualização e remoção com facilidade.
13. Possuir documentação de alta qualidade em português brasileiro.
14. Ser preparado para integração opcional com o ecossistema The Forge.
15. Manter o código simples, modular, testável e observável.
16. Não inventar resultados de benchmarks, métricas, testes ou diagnósticos.

## 0.2. Instrução de escopo

Este documento define o roadmap completo dos Cycles 01 a 08.

**Na primeira execução, implementar integralmente o Cycle 01 e preparar contratos e interfaces para os ciclos futuros.**

Não implementar os Cycles 02–08 superficialmente apenas para declarar conclusão.

A evolução deverá ser incremental, validada e baseada em entregas utilizáveis.

---

# 1. DESCOBERTA E PESQUISA TÉCNICA

Antes de desenvolver:

1. Investigue a estrutura e o estado do repositório de destino.
2. Identifique arquivos, componentes, documentação e testes existentes.
3. Preserve implementações válidas.
4. Identifique problemas de arquitetura e inconsistências.
5. Consulte a documentação oficial atual das tecnologias selecionadas.
6. Analise ferramentas e projetos open source consolidados.
7. Identifique oportunidades de reutilização em vez de reconstrução desnecessária.

Utilize ferramentas locais e, quando disponíveis:

- Skills de arquitetura de software.
- Skills de engenharia de dados.
- Skills AWS.
- Skills de Apache Spark.
- Skills de Python.
- Skills de SQL.
- Skills de segurança.
- Skills de engenharia agêntica.
- Skills de testes e QA.
- Skills de DevOps e CI/CD.
- Skills de MCP.
- Skills de UI/UX e Angular.
- Agentes de code review, planejamento e documentação.

Não presuma que uma skill ou agente existe. Descubra a capacidade instalada, avalie sua relevância e utilize-a quando trouxer benefícios verificáveis.

## 1.1. Projetos de referência

Investigue principalmente:

- OpenTelemetry — https://opentelemetry.io/
- Apache Spark — https://spark.apache.org/
- Apache Iceberg — https://iceberg.apache.org/
- AWS Glue — https://docs.aws.amazon.com/glue/
- AWS Lake Formation — https://docs.aws.amazon.com/lake-formation/
- AWS Athena — https://docs.aws.amazon.com/athena/
- OpenLineage — https://openlineage.io/
- Marquez — https://marquezproject.ai/
- Great Expectations — https://greatexpectations.io/
- Deequ — https://github.com/awslabs/deequ
- PyDeequ — https://github.com/awslabs/python-deequ
- SQLGlot — https://github.com/tobymao/sqlglot
- DataHub — https://datahubproject.io/
- OpenMetadata — https://open-metadata.org/
- LangGraph — https://github.com/langchain-ai/langgraph
- Model Context Protocol — https://modelcontextprotocol.io/

Investigue outras ferramentas relevantes, mas não adicione dependências apenas por popularidade.

Para cada solução considerada, documente:

- Capacidades existentes.
- Limitações.
- Maturidade.
- Licenciamento.
- Manutenção e compatibilidade.
- Possibilidade de integração.
- Benefícios e custos operacionais.
- Justificativa para utilizar, adaptar ou não adotar.

**O Data Sentinel deve competir por qualidade de integração, inteligência diagnóstica e experiência de uso, não pelo número de bibliotecas incorporadas.**

---

# 2. VISÃO DO PRODUTO

O Data Sentinel deverá ser composto por seis domínios funcionais.

## 2.1. Sentinel Diagnose

Motor de investigação técnica e análise de causa-raiz.

Capacidades previstas:

- Diagnóstico de falhas AWS Glue.
- Diagnóstico de erros Spark.
- Análise de logs CloudWatch.
- Investigação de problemas de leitura e escrita.
- Investigação de erros Iceberg.
- Investigação de permissões Lake Formation.
- Diagnóstico de falhas cross-account.
- Identificação de problemas de catálogo.
- Classificação de erros SQL.
- Análise de incompatibilidades entre runtimes.
- Correlação entre alterações de código, configuração e falhas.
- Histórico de incidentes e soluções.
- Geração de hipóteses com evidências.

O motor deve diferenciar:

**CONFIRMED:** problema demonstrado por evidência suficiente.

**PROBABLE:** hipótese com evidências relevantes, mas ainda não conclusivas.

**POSSIBLE:** hipótese plausível que precisa de validação.

**UNKNOWN:** evidências insuficientes para estabelecer a causa.

Cada diagnóstico deve informar:

- Identificador.
- Título.
- Categoria.
- Severidade.
- Confiança calibrada, quando disponível.
- Recursos afetados.
- Evidências.
- Hipóteses alternativas.
- Causa provável.
- Impacto esperado.
- Ações sugeridas.
- Procedimentos de verificação.
- Referências técnicas.
- Limitações da análise.

A palavra "confirmado" não deve ser utilizada apenas porque um LLM considera a resposta provável.

## 2.2. Sentinel Optimize

Motor especializado em performance.

Investigar:

- JOINs.
- Shuffle.
- Data skew.
- Partition pruning.
- Predicate pushdown.
- Broadcast joins.
- Sort-merge joins.
- Adaptive Query Execution.
- Distribuição de partições.
- Spill em disco.
- Uso de memória.
- Garbage collection.
- CPU e utilização de executores.
- Cache inadequado.
- Cardinalidade.
- Estatísticas de tabelas.
- Small files.
- Estratégias de leitura e escrita.
- Dimensionamento de workers.
- Custos de processamento.

Cada recomendação deve descrever o mecanismo técnico que justificaria a melhoria.

Não afirmar que uma otimização é mais rápida sem testes ou evidências apropriadas.

## 2.3. Sentinel Quality

Análise de qualidade e integridade de dados.

Capacidades:

- Unicidade.
- Completude.
- Integridade referencial.
- Duplicidade.
- Validação de schema.
- Schema drift.
- Freshness.
- Volumetria.
- Distribuição estatística.
- Regras de negócio.
- Data contracts.
- Detecção de anomalias.
- Validação pré e pós-processamento.

Fornecer arquitetura de adaptadores para:

- PyDeequ.
- Deequ.
- Great Expectations.
- SQL nativo.
- Validações DataFrame.

Evitar criar um framework completo de qualidade quando bibliotecas existentes puderem cumprir a função.

## 2.4. Sentinel Lineage

Construção de grafos de dependência.

Suportar conceitos como:

- Dataset.
- Tabela.
- Coluna.
- Job.
- Pipeline.
- Transformação.
- Fonte.
- Destino.
- Execução.
- Dependência.
- Impacto.
- Ownership.

Evoluir para lineage em nível de coluna quando tecnicamente viável.

O sistema deverá informar claramente a procedência e a confiança do lineage: declarado, inferido estaticamente ou observado em execução.

## 2.5. Sentinel Intelligence

Camada de inteligência agêntica.

Responsabilidades:

- Planejamento da investigação.
- Escolha de ferramentas.
- Delegação para especialistas.
- Consolidação de evidências.
- Identificação de hipóteses.
- Recuperação de conhecimento.
- Geração de recomendações.
- Validação de conclusões.
- Explicação técnica.
- Redução de uso de contexto.

Não utilizar LLM para tarefas resolvidas de forma confiável com regras determinísticas.

## 2.6. Sentinel Watch

Camada futura de monitoramento contínuo.

Capacidades:

- Comparação histórica entre execuções.
- Detecção de regressões.
- Alertas de anomalia.
- Correlação de incidentes.
- Monitoramento de SLAs.
- Análise de custos.
- Identificação de degradação gradual.
- Recomendações preventivas.
- Remediação supervisionada.

---

# 3. ARQUITETURA ALVO

Adotar arquitetura modular orientada a domínio, com separação entre núcleo de análise, integrações, inteligência, APIs e interface.

Não utilizar microsserviços como padrão inicial.

Preferir um modular monolith com interfaces bem definidas.

Estrutura conceitual:

```text
data-sentinel/
├── src/
│   └── data_sentinel/
│       ├── core/
│       │   ├── domain/
│       │   ├── contracts/
│       │   ├── models/
│       │   ├── exceptions/
│       │   ├── configuration/
│       │   └── security/
│       ├── analyzers/
│       │   ├── spark/
│       │   ├── sql/
│       │   ├── glue/
│       │   ├── iceberg/
│       │   ├── lakeformation/
│       │   ├── quality/
│       │   └── cost/
│       ├── connectors/
│       │   ├── aws/
│       │   ├── databricks/
│       │   ├── local/
│       │   └── telemetry/
│       ├── intelligence/
│       │   ├── agents/
│       │   ├── orchestration/
│       │   ├── retrieval/
│       │   ├── memory/
│       │   └── evaluation/
│       ├── lineage/
│       ├── diagnostics/
│       ├── persistence/
│       ├── cli/
│       ├── api/
│       ├── mcp/
│       └── observability/
├── portal/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── security/
│   ├── performance/
│   ├── regression/
│   └── e2e/
├── benchmarks/
├── fixtures/
├── docs/
├── examples/
├── schemas/
├── scripts/
├── .github/
├── pyproject.toml
└── README.md
```

Essa estrutura é uma referência arquitetural.

O time pode refiná-la durante o ADR inicial, desde que mantenha os limites modulares e evite abstrações desnecessárias.

## 3.1. Tecnologias preferenciais

Backend:

- Python 3.11+.
- Pydantic.
- Typer para CLI.
- FastAPI para API.
- HTTPX, quando necessário.
- SQLGlot para parsing SQL.
- Boto3 para integrações AWS.
- SQLAlchemy e Alembic quando justificáveis.
- SQLite para o ambiente local inicial.
- PostgreSQL como evolução opcional.
- Pytest.
- Ruff.
- Mypy ou Pyright.

Frontend futuro:

- Angular.
- TypeScript.
- Componentes acessíveis.
- Biblioteca de grafos adequada e mantida.
- Layout responsivo.
- Tema escuro e claro.
- Internacionalização PT-BR/EN.

Observabilidade:

- OpenTelemetry.
- Logs estruturados.
- Trace IDs.
- Métricas.
- Correlation IDs.

IA:

- Abstração de provider.
- Adaptadores para provedores compatíveis.
- Modelos locais opcionais.
- RAG híbrido quando justificado.
- GraphRAG quando houver benefício mensurável.
- Orquestração controlada por contratos.

Não adotar LangGraph, bancos vetoriais ou banco de grafos como obrigatórios no primeiro ciclo.

Todas as dependências devem ter justificativa.

---

# 4. CONTRATOS DE DOMÍNIO

Definir contratos públicos versionados e documentados.

Entidades mínimas:

**DiagnosticRequest**
- request_id
- source_type
- artifact_references
- execution_context
- platform
- runtime_version
- analysis_mode
- constraints

**Evidence**
- evidence_id
- source
- source_location
- captured_at
- content_hash
- sanitized_excerpt
- provenance
- confidence
- access_metadata

**Finding**
- finding_id
- category
- severity
- status
- explanation
- evidence_ids
- alternatives
- recommendations
- validation_steps

**DiagnosticReport**
- report_id
- schema_version
- request_id
- created_at
- environment
- analyzer_versions
- findings
- limitations
- summary
- references

**OptimizationRecommendation**
- recommendation_id
- target
- proposed_change
- rationale
- expected_effect
- estimated_risk
- validation_plan
- rollback_plan
- evidence_ids

**ExecutionMetadata**
- platform
- engine
- runtime
- run_id
- start_time
- end_time
- status
- resource_context

**CapabilityManifest**
- capability_id
- version
- supported_platforms
- supported_runtimes
- required_permissions
- supported_operations
- limitations

Implementar validação de schemas, serialização estável, testes de compatibilidade e regras explícitas de versionamento.

Separar contratos públicos dos tipos internos de implementação.

---

# 5. SISTEMA DE AGENTES ESPECIALISTAS

O Data Sentinel deverá possuir uma arquitetura agêntica real, desenvolvida progressivamente a partir do Cycle 05.

Não basta criar arquivos Markdown descrevendo papéis.

Cada agente deverá possuir:

- Responsabilidade.
- Escopo.
- Ferramentas permitidas.
- Entradas estruturadas.
- Saídas estruturadas.
- Critérios de sucesso.
- Limites de execução.
- Budget de contexto e tokens.
- Políticas de segurança.
- Estratégia de fallback.
- Testes.
- Indicadores de qualidade.

## 5.1. Agentes planejados

**Sentinel Coordinator**

Recebe solicitações e define o fluxo de investigação.

**Spark Performance Expert**

Analisa planos físicos, estágios, executores, JOINs, skew e shuffle.

**AWS Glue Expert**

Investiga configurações, execuções, logs, workers, versões e observabilidade.

**Iceberg Expert**

Especialista em snapshots, manifests, formatos de tabela, MERGE, UPDATE, DELETE, compactação e compatibilidade de runtimes.

**Lake Formation & IAM Expert**

Analisa autorizações, acesso cross-account, FGAC, FTA e requisitos de permissões.

**SQL Optimization Expert**

Analisa parsing, cardinalidade, predicados e estratégias de consulta.

**Data Quality Expert**

Investiga contratos, métricas e problemas de integridade.

**Data Lineage Expert**

Constrói relações, identifica dependências e avalia impacto.

**Cost Optimization Expert**

Avalia desperdícios e oportunidades de redução de custos.

**Root Cause Analyst**

Consolida evidências e diferencia sintomas de causas.

**Evidence Validator**

Valida o vínculo entre conclusões e evidências.

**Security Reviewer**

Inspeciona riscos, dados sensíveis e ações perigosas.

**Benchmark Engineer**

Executa testes comparativos controlados.

**Report Specialist**

Gera relatórios técnicos compreensíveis.

## 5.2. Orquestração

Fluxo conceitual:

```text
Request
   |
   v
Sentinel Coordinator
   |
   v
Deterministic Triage
   |
   +--> Spark Expert
   +--> Glue Expert
   +--> Iceberg Expert
   +--> Security Expert
   +--> SQL Expert
   |
   v
Evidence Aggregator
   |
   v
Root Cause Analyst
   |
   v
Evidence Validator
   |
   v
Diagnostic Report
```

Implementar seleção dinâmica de especialistas baseada no tipo de problema.

Evitar executar todos os agentes em todas as solicitações.

Impor limites de profundidade, número de chamadas, tempo de execução, custo e tentativas.

Um agente não poderá classificar como comprovado um problema sem evidências adequadas.

---

# 6. CONTEXT ENGINEERING E ECONOMIA

O Data Sentinel deve aproveitar boas práticas aprendidas no ecossistema The Forge sem depender dele.

Implementar progressivamente:

- Contexto mínimo necessário.
- Recuperação sob demanda.
- Compressão sem perda de fatos relevantes.
- Cache por hash de conteúdo.
- Deduplicação de evidências.
- Seleção inteligente de ferramentas.
- Model routing por complexidade.
- Limites de tokens.
- Limites de custo.
- Contagem de tool calls.
- Prevenção de loops.
- Resumos estruturados.
- Invalidação de cache.
- Observabilidade de uso de modelos.

Perfis previstos:

**economy:** prioriza análise determinística e custo reduzido.

**balanced:** equilíbrio entre profundidade e consumo.

**deep:** investigação aprofundada e múltiplas verificações.

**offline:** sem chamadas externas e sem exigência de modelo de IA.

Todos os perfis devem preservar a segurança e a confiabilidade.

A métrica principal não é simplesmente gastar menos tokens, mas maximizar diagnósticos corretos por custo total de investigação.

---

# 7. INTEGRAÇÃO COM THE FORGE

Referências do ecossistema:

- https://github.com/EdgarSocrates98/the-forge
- https://github.com/EdgarSocrates98/spark-forge-aws
- https://github.com/EdgarSocrates98/spark-forge-azure
- https://github.com/EdgarSocrates98/api-forge
- https://github.com/EdgarSocrates98/platform-forge
- https://github.com/EdgarSocrates98/forge-cli
- https://github.com/EdgarSocrates98/forge-portal

Examinar os contratos públicos e as interfaces reais antes de planejar integrações concretas.

Não assumir que APIs, ferramentas MCP ou capabilities específicas já existem.

## 7.1. Independência

O Data Sentinel:

- Deve instalar e funcionar sem The Forge.
- Não deve importar módulos internos de outras Forjas.
- Não deve exigir Forge CLI.
- Não deve depender de Forge Portal.
- Deve expor capacidades próprias.
- Deve fornecer MCP opcional.
- Deve permitir integração por protocolos públicos.
- Deve aceitar discovery externo quando disponível.

The Forge poderá descobrir e orquestrar capacidades do Sentinel por integração explícita e versionada.

## 7.2. Responsabilidades

Spark Forge AWS:

Padrões, geração, implementação e boas práticas de workloads AWS.

Data Sentinel:

Investigação operacional, evidências, diagnóstico e recomendações de otimização.

Forge Doctor:

Validações especializadas já definidas em seus respectivos domínios.

Forge Portal:

Administração do ecossistema e descoberta de capacidades, sem assumir automaticamente a função de portal analítico do Sentinel.

Evitar sobreposição funcional desnecessária.

---

# 8. ROADMAP COMPLETO

# CYCLE 01 — FOUNDATION & CONTRACTS

## Objetivo

Estabelecer um núcleo executável, seguro, testável e independente.

Este é o único ciclo autorizado para implementação completa na primeira execução.

### Fase 01.1 — Repository Foundation

- Criar ou adequar estrutura Python moderna.
- Configurar `pyproject.toml`.
- Definir versão mínima de Python.
- Configurar build e instalação.
- Criar CLI inicial.
- Configurar lint e type checking.
- Configurar testes.
- Configurar CI.
- Configurar tratamento de erros.
- Configurar logs estruturados.
- Criar documentação inicial.
- Criar política de versionamento.
- Adicionar licença open source adequada.
- Adicionar CONTRIBUTING, SECURITY e CODE_OF_CONDUCT.
- Garantir suporte Linux, Windows e macOS sempre que viável.

### Fase 01.2 — Core Domain

Implementar os contratos de domínio definidos anteriormente.

Criar:

- Modelos Pydantic.
- Enums e tipos controlados.
- Validadores.
- Exceções de domínio.
- Serializadores.
- Schema version.
- Testes de round-trip.
- Testes de compatibilidade.
- JSON Schemas públicos.

### Fase 01.3 — Analyzer Protocol

Estabelecer uma interface extensível para analisadores.

Capacidades:

- Identificar formatos suportados.
- Declarar plataformas compatíveis.
- Validar inputs.
- Executar análise.
- Retornar achados estruturados.
- Declarar limitações.
- Registrar evidências.

Implementar pelo menos um analisador determinístico funcional, usando artefatos locais e fixtures.

Preferencialmente, criar um analisador de logs Spark/Glue com padrões de erro conhecidos e um analisador básico de SQL estático, desde que ambos sejam suficientemente testados.

Não incluir análises fictícias.

### Fase 01.4 — CLI

Implementar uma CLI utilizável.

Comandos iniciais propostos:

```bash
data-sentinel --help
data-sentinel version
data-sentinel doctor
data-sentinel capabilities
data-sentinel analyze --file job.log
data-sentinel analyze --sql query.sql
data-sentinel report --input report.json
data-sentinel config show
```

Os comandos devem oferecer:

- `--help` útil.
- Mensagens PT-BR.
- `--json` para automação.
- Exit codes estáveis.
- Logs opcionais.
- Modo não interativo.
- Tratamento amigável de erros.

Não disponibilizar comandos sem implementação funcional.

### Fase 01.5 — Configuration

Criar sistema de configuração com precedência documentada:

1. Argumentos da CLI.
2. Variáveis de ambiente.
3. Configuração do projeto.
4. Configuração do usuário.
5. Valores padrão seguros.

Evitar persistir segredos em texto puro.

Implementar:

- Perfis.
- Validação de configuração.
- Redação de credenciais em logs.
- Descoberta de configurações.
- Diagnóstico de instalação.

### Fase 01.6 — Persistence

Implementar armazenamento local mínimo para:

- Relatórios.
- Histórico de análise.
- Metadados.
- Evidências sanitizadas.

Utilizar SQLite se a persistência for necessária ao primeiro fluxo completo.

Não introduzir infraestrutura distribuída.

Implementar migrações quando houver schema persistente.

### Fase 01.7 — Security Foundation

- Read-only por padrão.
- Nenhuma necessidade de credenciais AWS para análises locais.
- Sanitização de entradas.
- Proteção contra path traversal.
- Limites de tamanho dos arquivos.
- Limites de processamento.
- Redação de secrets.
- Proteção contra leitura arbitrária de caminhos.
- Proibição de execução de comandos extraídos de logs ou arquivos.
- Uso restrito de subprocessos.
- Dependências verificadas.
- Tratamento de entradas malformadas.

### Fase 01.8 — Testes

Implementar:

- Testes unitários.
- Testes de integração local.
- Testes de contratos.
- Testes de CLI.
- Testes de entradas inválidas.
- Testes de segurança.
- Testes de serialização.
- Testes de compatibilidade.
- Smoke tests de instalação.

Estabelecer meta inicial de 85% de cobertura no núcleo novo, sem utilizar a porcentagem como substituto de testes significativos.

A CI deve executar os testes obrigatórios.

### Fase 01.9 — Documentação

Criar:

- README PT-BR.
- Guia rápido.
- Guia de instalação.
- Guia de configuração.
- Guia da CLI.
- Guia de arquitetura.
- Guia de desenvolvimento.
- ADRs.
- Roadmap.
- Exemplos reproduzíveis.
- Troubleshooting.
- Guia de segurança.

### Aceite do Cycle 01

O ciclo estará concluído somente quando:

- O pacote instalar com sucesso.
- A CLI funcionar.
- Existir análise local determinística real.
- Relatórios estruturados forem produzidos.
- Evidências forem rastreáveis.
- A execução offline funcionar.
- A CI estiver verde.
- Os testes relevantes passarem.
- O sistema não depender das Forjas.
- A documentação permitir utilização independente.
- Não existirem funcionalidades falsas ou mocks apresentados como produção.

---

# CYCLE 02 — SPARK & GLUE INTELLIGENCE

## Objetivo

Construir o primeiro conjunto avançado de capacidades diagnósticas.

### Fase 02.1 — AWS Glue Connector

Implementar integração read-only usando Boto3.

Suportar, conforme permissões:

- Listagem de jobs.
- Consulta de definições.
- Consulta de runs.
- Metadados de execução.
- Consulta de status.
- Recuperação de configurações.
- Consulta de métricas.
- Acesso autorizado a logs.
- Comparação entre execuções.

Evitar alterar a configuração dos jobs.

### Fase 02.2 — CloudWatch Diagnostics

Implementar análise de:

- Erros.
- Timeouts.
- Falhas de executores.
- Out of memory.
- Spills.
- Falhas de leitura/escrita.
- Exceções Spark.
- Problemas de permissões.
- Regressões de execução.

Respeitar paginação, throttling, limites de API, custo de leitura de logs e retenção.

### Fase 02.3 — Spark Plan Analyzer

Analisar planos físicos e lógicos exportados.

Identificar:

- SortMergeJoin.
- BroadcastHashJoin.
- ShuffleHashJoin.
- Exchange.
- Sort.
- Scan.
- Filter.
- Aggregate.
- Repartition.
- Coalesce.
- AdaptiveSparkPlan.
- Operações associadas a spill.

Criar parsing tolerante a diferentes formatos e versões.

Caso a informação não esteja disponível, declarar explicitamente a limitação.

### Fase 02.4 — JOIN Intelligence

Investigar:

- Cardinalidade estimada.
- Crescimento de linhas intermediárias.
- Chaves duplicadas.
- Fan-out.
- Skew.
- Seletividade.
- Estatísticas ausentes.
- Estratégia de JOIN.
- Complexidade do plano.

Diferenciar estimativas de observações reais.

### Fase 02.5 — SQL Analyzer

Utilizar parser SQL consolidado.

Suportar dialetos inicialmente priorizados:

- Spark SQL.
- Athena/Trino.

Evitar tratar os dois motores como equivalentes.

Investigar:

- JOINs.
- Subqueries.
- CTEs.
- Predicados.
- Projeções.
- Agregações.
- Ordenações.
- Possíveis filtros tardios.
- Relações entre tabelas.
- Antipadrões.

A análise estática não deve fingir conhecer a estratégia física real de execução.

### Fase 02.6 — Spark Configuration Advisor

Avaliar:

- AQE.
- Shuffle partitions.
- Broadcast threshold.
- Executor memory.
- Worker configuration.
- Dynamic allocation, quando aplicável.
- Paralelismo.
- Recursos disponíveis.
- Limites por runtime.

Propor alterações condicionais com justificativas, pré-requisitos e plano de medição.

### Cenário obrigatório de homologação

Criar cenário reproduzível envolvendo quatro relações com volumetrias conceituais de:

- 230 milhões de registros.
- 73 milhões de registros.
- 230 milhões de registros.
- 250 milhões de registros.

Utilizar inicialmente estatísticas e dados sintéticos pequenos.

Não exigir a geração física de centenas de milhões de linhas.

Testar:

- Cardinalidade.
- Duplicidades nas chaves.
- Fan-out.
- Ordem lógica das operações.
- Estratégias de JOIN.
- Regras de otimização.
- Limitações de evidência.

---

# CYCLE 03 — ICEBERG, LAKE FORMATION & SECURITY

## Objetivo

Criar diagnóstico profundo de ambientes AWS Lakehouse.

### Fase 03.1 — Iceberg Analyzer

Investigar:

- Snapshots.
- Manifests.
- Metadata files.
- Partition specs.
- Schema evolution.
- Delete files.
- Small files.
- MERGE INTO.
- UPDATE.
- DELETE.
- APPEND.
- Estratégias copy-on-write e merge-on-read.
- Compatibilidade de versões.
- Catálogos.

Distinguir Glue Data Catalog, Glue Catalog, S3 Tables e outras formas de catálogo conforme os serviços e APIs efetivamente disponíveis.

### Fase 03.2 — Lake Formation Expert

Construir matriz de compatibilidade versionada considerando:

- Runtime Glue.
- Versão Spark.
- Versão Iceberg.
- Modo FGAC.
- Modo FTA.
- Operação desejada.
- Tipo de tabela.
- Catálogo.
- Permissões IAM.
- Permissões Lake Formation.
- Cross-account.
- Região e disponibilidade do recurso.

**Não assumir que FGAC impede toda escrita.**

No Glue 5.1 há suporte expandido a operações de escrita em cenários FGAC suportados; validar detalhes e limitações na documentação oficial atual.

Identificar erros relacionados a credenciais temporárias e autorização sem sugerir permissões excessivas.

### Fase 03.3 — Cross-account Diagnostics

Investigar:

- Account origem.
- Account destino.
- Catálogo.
- Compartilhamento de recursos.
- Resource links.
- IAM.
- Lake Formation.
- S3.
- KMS.
- Sessões e credenciais.
- Caminhos de leitura e escrita.

Nunca tentar ler recursos não autorizados.

Não executar alterações de políticas automaticamente.

### Fase 03.4 — Compatibility Knowledge Base

Criar base de regras com:

- Fonte oficial.
- Data de verificação.
- Versões abrangidas.
- Região, quando relevante.
- Restrições.
- Condições.
- Exemplos.
- Status de validade.

Regras desatualizadas deverão poder ser desativadas ou marcadas como não verificadas.

### Aceite

O sistema deve distinguir falhas de:

- Autenticação.
- Autorização.
- Configuração de catálogo.
- Compatibilidade de runtime.
- Sintaxe.
- Operação não suportada.
- Falhas de leitura.
- Falhas de escrita.

Testar com fixtures sintéticas, ambiente isolado e, opcionalmente, integração AWS autorizada.

---

# CYCLE 04 — DATA QUALITY & LINEAGE

## Objetivo

Incorporar qualidade de dados e análise de impacto.

### Fase 04.1 — Data Quality Contracts

Implementar contratos declarativos versionados.

Suportar:

- Schema.
- Tipos.
- Campos obrigatórios.
- Unicidade.
- Chaves.
- Constraints.
- Regras customizadas.
- Freshness.
- Volumetria.
- Expectativas estatísticas.

### Fase 04.2 — Quality Adapters

Criar adaptadores para ferramentas existentes.

Separar:

- Definição da regra.
- Execução.
- Coleta de resultado.
- Agregação.
- Relatório.

Evitar executar scans caros automaticamente.

### Fase 04.3 — Data Lineage

Integrar padrões de OpenLineage sempre que adequados.

Criar modelo de grafo para datasets, jobs e transformações.

Suportar:

- Upstream.
- Downstream.
- Impact analysis.
- Dependências entre jobs.
- Histórico.
- Proveniência.
- Exportação de grafo.

### Fase 04.4 — Graph Visualization Contract

Definir contrato de nós e arestas para a futura UI.

A estrutura deve permitir:

- ID estável.
- Tipo.
- Metadados.
- Fonte.
- Confiança.
- Relacionamentos.
- Filtros.
- Agrupamentos.
- Expansão progressiva.

---

# CYCLE 05 — AGENTIC INTELLIGENCE

## Objetivo

Construir inteligência agêntica especializada sobre as evidências geradas pelos motores determinísticos.

### Fase 05.1 — Agent Runtime

Implementar runtime controlado com:

- Planejamento.
- Delegação.
- Execução de ferramentas.
- Resolução de dependências.
- Cancelamento.
- Timeouts.
- Retry limitado.
- Logs e traces.
- Limites de custo.
- Limites de chamadas.
- Policy checks.

### Fase 05.2 — Specialist Agents

Implementar progressivamente os agentes definidos na seção 5.

Cada agente deve possuir testes de:

- Competência.
- Seleção de ferramentas.
- Saída estruturada.
- Recusa de ações não autorizadas.
- Tratamento de evidências insuficientes.
- Falhas de provider.
- Consumo de recursos.

### Fase 05.3 — RAG

Implementar retrieval híbrido quando justificado:

- Busca lexical.
- Busca vetorial.
- Metadata filtering.
- Ranking.
- Deduplicação.
- Referência de origem.
- Expiração.
- Controle de acesso.

Documentos não confiáveis não devem poder alterar instruções, autorizações ou políticas do agente.

### Fase 05.4 — GraphRAG

Avaliar construção de grafo de conhecimento relacionando:

- Jobs.
- Tabelas.
- Incidentes.
- Diagnósticos.
- Erros.
- Soluções.
- Dependências.
- Configurações.

Medir ganho efetivo contra recuperação lexical e vetorial tradicional antes de torná-lo componente padrão.

### Fase 05.5 — MCP Server

Expor ferramentas de análise em modo seguro.

Ferramentas candidatas:

```text
sentinel.capabilities
sentinel.analyze_file
sentinel.analyze_sql
sentinel.explain_report
sentinel.get_findings
sentinel.get_evidence
sentinel.compare_runs
sentinel.inspect_glue_job
sentinel.inspect_glue_run
sentinel.analyze_spark_plan
sentinel.analyze_iceberg_metadata
sentinel.inspect_access_model
sentinel.recommend_optimization
```

Expor somente ferramentas efetivamente implementadas.

Classificar ferramentas por permissões.

Proteger contra parâmetros maliciosos, acesso indevido a arquivos e exfiltração.

### Fase 05.6 — Evaluation Harness

Criar datasets de avaliação e mecanismos para:

- Correção factual.
- Qualidade das evidências.
- Taxa de diagnósticos incorretos.
- Cobertura.
- Latência.
- Custo.
- Tokens.
- Tool calls.
- Reprodutibilidade.

---

# CYCLE 06 — SENTINEL CONTROL CENTER

## Objetivo

Criar interface Angular profissional para investigação, exploração de dados e observabilidade.

### Fase 06.1 — Design System

Identidade visual própria do Data Sentinel, coerente com o ecossistema The Forge.

Diretrizes:

- Interface moderna.
- Dark mode e light mode.
- Acessibilidade.
- Hierarquia visual clara.
- Responsividade.
- Microinterações discretas.
- Animações úteis.
- PT-BR como idioma principal.
- EN como idioma secundário.
- Performance visual.

Utilizar skills e agentes especializados em UI, UX, design system e Angular.

### Fase 06.2 — Dashboard

Exibir:

- Análises recentes.
- Jobs investigados.
- Severidades.
- Status.
- Incidentes.
- Tendências.
- Indicadores de performance.
- Resultados de recomendações.
- Evidências coletadas.

Não exibir métricas ou dados fabricados como reais.

### Fase 06.3 — Investigation Workspace

Criar fluxo interativo:

1. Selecionar fonte ou importar arquivo.
2. Escolher tipo de análise.
3. Visualizar progresso.
4. Explorar achados.
5. Visualizar evidências.
6. Comparar hipóteses.
7. Inspecionar recomendações.
8. Exportar relatório.

### Fase 06.4 — Graph Explorer

Permitir visualizar:

- Vértices.
- Arestas.
- Tipos de nós.
- Dependências.
- Lineage.
- Impacto.
- Agrupamentos.
- Caminhos.
- Animações de fluxo.

Exigir zoom, pan, busca, filtros e expansão progressiva.

O grafo deve permanecer navegável com milhares de elementos mediante agregação e renderização eficiente.

### Fase 06.5 — Spark Plan Explorer

Criar visualização específica de planos Spark.

Mostrar:

- Operadores.
- JOINs.
- Exchanges.
- Estágios.
- Dependências.
- Gargalos identificados.
- Evidências de skew.
- Métricas disponíveis.

Não confundir estrutura lógica com execução observada.

### Fase 06.6 — Report Explorer

Exibir relatórios com:

- Severidade.
- Confiança.
- Evidências.
- Recomendações.
- Comparações.
- Exportação JSON/Markdown.
- Histórico.

### Fase 06.7 — Authentication & Authorization

Quando o portal suportar recursos remotos ou dados de múltiplos usuários, implementar autenticação, autorização e isolamento apropriados.

Não expor logs ou metadados sensíveis a usuários não autorizados.

---

# CYCLE 07 — AUTONOMOUS OPERATIONS

## Objetivo

Evoluir para operações assistidas e preventivas.

### Fase 07.1 — Historical Analysis

Comparar execuções usando:

- Duração.
- Custo.
- Volume.
- Falhas.
- Métricas Spark.
- Recursos.
- Versão de código.
- Configuração.

### Fase 07.2 — Regression Detection

Identificar:

- Aumento de duração.
- Aumento de shuffle.
- Queda de throughput.
- Crescimento de small files.
- Aumento de custo.
- Alterações de cardinalidade.
- Mudanças de distribuição.

Aplicar métodos adequados à quantidade e qualidade do histórico.

### Fase 07.3 — Cost Intelligence

Avaliar oportunidades de redução de custos.

Diferenciar:

- Custo observado.
- Custo estimado.
- Estimativa incompleta.
- Economia potencial.
- Economia comprovada.

### Fase 07.4 — Remediation Planning

Gerar propostas de correção.

Cada proposta deve conter:

- Evidências.
- Alteração sugerida.
- Justificativa.
- Risco.
- Testes necessários.
- Plano de aplicação.
- Plano de rollback.
- Critérios de sucesso.

### Fase 07.5 — Controlled Remediation

Implementar somente após aprovação específica do usuário e autorizações verificáveis.

Exigir:

- Dry-run.
- Diff.
- Permissões mínimas.
- Aprovação humana.
- Logs de auditoria.
- Validação pós-ação.
- Rollback viável.

O Data Sentinel nunca deve alterar dados produtivos silenciosamente.

---

# CYCLE 08 — PRODUCTION, BENCHMARKS & OPEN SOURCE

## Objetivo

Preparar o produto para utilização contínua e adoção externa.

### Fase 08.1 — Hardening

- Revisão de segurança.
- Testes de carga.
- Testes de concorrência.
- Limites de memória.
- Revisão de dependências.
- Tratamento de falhas.
- Compatibilidade entre versões.
- Recovery.
- Observabilidade.

### Fase 08.2 — Benchmark Suite

Criar benchmarks reproduzíveis para:

- Diagnóstico de erros.
- Análise de Spark.
- Análise SQL.
- Iceberg.
- Permissões AWS.
- Qualidade de dados.
- Lineage.
- Agentes.
- Consumo de tokens.
- Custo de análise.

Exigir comparação com baseline.

Não divulgar ganhos percentuais sem testes reproduzíveis.

### Fase 08.3 — Publication

Preparar:

- PyPI.
- Releases GitHub.
- Versionamento semântico.
- Changelog.
- Artifacts.
- Provenance.
- SBOM.
- CI/CD.
- Publicação segura por OIDC ou mecanismo equivalente adequado.
- Documentação de distribuição.

### Fase 08.4 — Ecosystem Integration

Validar:

- Uso independente.
- Uso com The Forge.
- Uso com Spark Forge AWS.
- Uso do MCP.
- Uso via CLI.
- Uso via API.
- Uso via portal.
- Instalação limpa.
- Reinstalação.
- Atualização.
- Desinstalação.

---

# 9. CENÁRIOS REAIS OBRIGATÓRIOS

Criar uma suíte de cenários que evoluirá ao longo do roadmap.

## Cenário A — JOINs de alta volumetria

Query com quatro tabelas de aproximadamente:

230M, 73M, 230M e 250M registros.

Avaliar:

- Estratégia de JOIN.
- Cardinalidade.
- Duplicidade.
- Skew.
- Shuffle.
- Filtros.
- Seleção de colunas.
- Impacto de estatísticas.
- Estratégias alternativas.

## Cenário B — Glue 5.1 cross-account

Leitura de tabela Iceberg em outra conta AWS e gravação em conta de destino.

Investigar:

- Catálogo.
- Role.
- Permissões.
- Lake Formation.
- IAM.
- KMS.
- FGAC/FTA.
- Configuração Spark.
- Compatibilidade de escrita.
- MERGE INTO.
- APPEND.

## Cenário C — Iceberg MERGE

Simular operação incremental com deduplicação.

Validar:

- Chaves.
- Duplicidade.
- Matched/Not matched.
- Integridade.
- Idempotência.
- Particionamento.
- Performance.
- Compatibilidade.

## Cenário D — Spark skew

Criar dataset sintético com chave desbalanceada.

Comparar plano e comportamento com cenários balanceados.

## Cenário E — Small files

Criar metadata e fixtures que representem excesso de arquivos pequenos.

Gerar recomendações condicionais de manutenção.

## Cenário F — Erro de autorização

Fornecer logs e configurações com autorização insuficiente.

O sistema deverá identificar a possível camada responsável sem sugerir permissões administrativas amplas.

## Cenário G — Data quality regression

Simular queda de qualidade entre duas execuções.

Gerar comparação estruturada.

## Cenário H — Ausência de evidências

Fornecer informações insuficientes.

O sistema deverá explicitar o que não pode concluir e quais artefatos adicionais seriam úteis.

---

# 10. REQUISITOS NÃO FUNCIONAIS

## Segurança

- Least privilege.
- Read-only por padrão.
- Credential isolation.
- Sanitização.
- Proteção de dados.
- Audit logs.
- Redação de secrets.
- Proteção contra prompt injection.
- Supply-chain security.
- Controle de ferramentas e permissões.

## Performance

- Processamento incremental.
- Streaming de logs quando adequado.
- Limites de payload.
- Cache controlado.
- Paginação.
- Cancelamento.
- Timeouts.
- Evitar carregar grandes datasets na memória local.

## Confiabilidade

- Erros estruturados.
- Resultados parciais claramente sinalizados.
- Idempotência quando aplicável.
- Retry limitado.
- Circuit breakers quando justificáveis.
- Versionamento de contratos.

## Portabilidade

- Linux.
- Windows.
- macOS.
- CI reproduzível.
- Instalação independente.
- Containers opcionais.
- Dependências AWS opcionais.

## Observabilidade

- Logs estruturados.
- Métricas.
- Traces.
- Correlation IDs.
- Histórico de diagnósticos.
- Medição de custos.

## Qualidade

- Code review.
- Type checking.
- Lint.
- Testes de contratos.
- Testes de regressão.
- ADRs.
- Documentação atualizada.
- Builds reproduzíveis.

---

# 11. ESTRATÉGIA DE EXECUÇÃO AGÊNTICA

Antes de implementar:

1. Fazer descoberta do ambiente.
2. Identificar skills e agents disponíveis.
3. Inspecionar estado do repositório.
4. Criar inventário de capacidades.
5. Produzir arquitetura inicial.
6. Registrar ADRs importantes.
7. Quebrar Cycle 01 em tarefas verificáveis.
8. Ordenar tarefas por dependência.
9. Implementar incrementalmente.
10. Executar testes.
11. Revisar segurança.
12. Auditar arquitetura.
13. Validar critérios de aceite.
14. Produzir relatório final.

Utilizar subagentes especializados quando disponíveis, mas nunca delegar tarefas sem limites claros.

Executar tarefas paralelamente apenas quando houver independência suficiente para evitar conflitos.

Não confundir geração de código com conclusão de uma funcionalidade.

Exigir validação por um agente ou processo diferente daquele que implementou a mudança sempre que viável.

---

# 12. POLÍTICA DE GIT E CI/CD

- Não reescrever histórico desnecessariamente.
- Não realizar force-push sem autorização.
- Não expor segredos.
- Criar commits pequenos e descritivos.
- Utilizar branches e PRs quando o fluxo permitir.
- Validar lint, typing e testes antes de propor merge.
- Não modificar branch protegida sem autorização.
- Não iniciar publicação no PyPI sem aprovação.
- Não executar operações destrutivas.
- Documentar mudanças relevantes.

A presença de uma action configurada não significa que a CI passou.

Verificar resultados reais.

Quando alguma verificação não puder ser executada, informar exatamente o motivo.

---

# 13. MATRIZ DE VALIDAÇÃO

Para cada funcionalidade entregue, produzir:

| Dimensão | Evidência exigida |
|---|---|
| Funcional | Teste executado |
| Contrato | Schema validado |
| Segurança | Cenários relevantes |
| CLI | Comando executado |
| Compatibilidade | Ambiente identificado |
| Performance | Medição quando aplicável |
| Documentação | Exemplo funcional |
| Integração | Teste apropriado |
| Regressão | Suíte executada |
| CI | Resultado verificado |

Não utilizar "Done" ou "Completed" quando critérios de aceite não forem comprovados.

Usar os estados:

- COMPLETE
- PARTIAL
- BLOCKED
- NOT STARTED

---

# 14. ENTREGÁVEIS DO CYCLE 01

Ao concluir a execução inicial, entregar obrigatoriamente:

1. Estrutura funcional do repositório.
2. Pacote Python instalável.
3. CLI operacional.
4. Contratos públicos versionados.
5. Núcleo de análise determinística.
6. Pelo menos um diagnóstico real reproduzível.
7. Relatório JSON válido.
8. Renderização de relatório legível.
9. Configuração segura.
10. Testes automatizados.
11. CI configurada e validada quando disponível.
12. Documentação completa de uso inicial.
13. ADRs arquiteturais.
14. Roadmap técnico detalhado.
15. Backlog priorizado do Cycle 02.
16. Relatório de riscos e dívida técnica.
17. Evidências dos critérios de aceite.
18. Matriz de funcionalidades implementadas e planejadas.

Não criar apenas skeletons vazios para satisfazer a lista.

---

# 15. FORMATO DO RELATÓRIO FINAL

Ao finalizar, apresentar:

## Executive Summary

O que foi efetivamente entregue.

## Architecture

Decisões e estrutura.

## Implemented Capabilities

Funcionalidades utilizáveis.

## Validation Evidence

Comandos, testes e resultados reais.

## Security Review

Riscos encontrados e resolvidos.

## Compatibility

Ambientes testados e não testados.

## Open Issues

Pendências reais, classificadas P0/P1/P2.

## Next Cycle

Plano detalhado do Cycle 02.

## Final Status

Classificar o Cycle 01 como:

- APPROVED
- APPROVED WITH RESTRICTIONS
- NOT APPROVED

Justificar o resultado com evidências.

---

# 16. DIRETRIZES FINAIS E CRITÉRIO DE EXCELÊNCIA

O Data Sentinel não deve ser desenvolvido como uma demonstração superficial de IA.

Ele deve representar uma ferramenta real de engenharia.

Os melhores resultados deverão vir da combinação de:

**Análise determinística + Telemetria real + Conhecimento técnico + Inteligência agêntica + Evidências auditáveis.**

Não reinventar tecnologias consolidadas sem justificativa.

Não acrescentar complexidade arquitetural para aparentar sofisticação.

Não produzir dashboards que apenas exibem dados sem ajudar na investigação.

Não produzir agentes que apenas encapsulam prompts genéricos.

Não afirmar causas-raiz sem evidências.

Não realizar alterações em recursos cloud sem autorização.

Não sacrificar segurança para aumentar automação.

Não integrar obrigatoriamente nenhuma Forge.

Não buscar cobertura de features em detrimento de qualidade.

Priorizar utilidade prática, experiência de desenvolvimento, clareza técnica, extensibilidade, observabilidade e confiança.

## MISSÃO IMEDIATA

**Inicie agora a descoberta técnica e implemente o Cycle 01 — Foundation & Contracts de ponta a ponta.**

Prepare a arquitetura para todos os ciclos seguintes, mas entregue agora um primeiro produto funcional que possa ser instalado, utilizado, testado e validado.

Sempre que possível, utilize as skills, agentes, subagentes, ferramentas MCP e capacidades especializadas disponíveis no ambiente de desenvolvimento, sem presumir sua existência.

Só declare o Cycle 01 concluído quando seus critérios de aceite estiverem comprovados.

**DATA SENTINEL — Understand the data. Diagnose the system. Prove the solution.**
