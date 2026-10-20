/**
 * Translation dictionaries. `pt-BR` is the primary locale and must be
 * complete; `en` is the fallback locale (missing keys in any locale
 * fall back to `en`, then to the raw key).
 */

export interface TranslationDict {
  [key: string]: string;
}

export const PT_BR: TranslationDict = {
  "app.name": "Data Sentinel",
  "app.subtitle": "Control Center",

  "a11y.skipToContent": "Pular para o conteúdo",
  "a11y.primaryNav": "Navegação principal",
  "a11y.topbar": "Barra superior",
  "a11y.notifications": "Notificações",
  "a11y.dismiss": "Dispensar notificação",

  "nav.dashboard": "Visão geral",
  "nav.investigations": "Investigações",
  "nav.evidenceGraph": "Grafo de evidências",
  "nav.workloads": "Workloads",
  "nav.sparkPlans": "Planos Spark",
  "nav.qualityLineage": "Qualidade e linhagem",
  "nav.agents": "Agentes",
  "nav.reports": "Relatórios",

  "theme.toLight": "Alternar para tema claro",
  "theme.toDark": "Alternar para tema escuro",
  "lang.switch": "Switch to English",

  "status.underConstruction": "Em construção",
  "status.plannedCapabilities": "Capacidades planejadas",
  "status.apiConnected": "API conectada",
  "status.apiUnreachable": "API indisponível",
  "status.loading": "Carregando…",
  "status.retry": "Tentar novamente",

  "pages.dashboard.title": "Visão geral",
  "pages.dashboard.lead":
    "Estado da plataforma Data Sentinel e da API do Control Center.",
  "pages.dashboard.apiCard.title": "API do Control Center",
  "pages.dashboard.apiCard.version": "Versão do núcleo",
  "pages.dashboard.apiCard.api": "Versão da API",
  "pages.dashboard.apiCard.endpoint": "Endpoint",
  "pages.dashboard.apiCard.hint":
    "Inicie a API com `sentinel-api` (uvicorn em 127.0.0.1:8790) para conectar.",
  "pages.dashboard.capsCard.title": "Capacidades registradas",
  "pages.dashboard.capsCard.caps": "capacidades",
  "pages.dashboard.capsCard.tools": "ferramentas",
  "pages.dashboard.capsCard.agents": "agentes especializados",
  "pages.dashboard.capsCard.empty":
    "Sem dados — a API ainda não respondeu.",
  "pages.dashboard.scope.title": "Escopo desta versão",
  "pages.dashboard.scope.body":
    "Fundação Angular + design system. Os studios de investigação, grafo de evidências, workloads, planos Spark, qualidade, agentes e relatórios estão mapeados como rotas reais mínimas e serão implementados nas próximas fases — nenhuma funcionalidade é simulada.",

  "pages.investigations.title": "Investigações",
  "pages.investigations.lead":
    "Workspace principal: iniciar e acompanhar investigações diagnósticas com evidências, hipóteses e recomendações.",
  "pages.investigations.planned.0":
    "Seleção de fonte (Glue Job Run, artefatos EMR, SQL, EXPLAIN Spark, logs CloudWatch, Iceberg, observações de qualidade, eventos OpenLineage, doctor bundle)",
  "pages.investigations.planned.1":
    "Perfis de investigação e visualização das permissões necessárias",
  "pages.investigations.planned.2":
    "Acompanhamento de progresso via stream de eventos (SSE)",
  "pages.investigations.planned.3":
    "Painéis: resumo, atividade dos agentes, findings, evidências, hipóteses, linha do tempo e recomendações",
  "pages.investigations.planned.4":
    "Inspetor de evidências com origem, proveniência, hash, confiança e limitações",
  "pages.investigations.planned.5": "Exportação de relatório",

  "pages.evidenceGraph.title": "Grafo de evidências",
  "pages.evidenceGraph.lead":
    "Explorador do grafo de evidências: nós, relações e caminhos entre jobs, datasets, findings e hipóteses.",
  "pages.evidenceGraph.planned.0":
    "Nós: Job, Run, Dataset, Stage Spark, Evento de log, Evidência, Finding, Hipótese, Agente, Ferramenta, Snapshot Iceberg, Observação de qualidade",
  "pages.evidenceGraph.planned.1":
    "Arestas: READS, WRITES, PRODUCES, DEPENDS_ON, SUPPORTED_BY, ASSOCIATED_WITH, POTENTIALLY_CAUSED_BY, VALIDATED_BY",
  "pages.evidenceGraph.planned.2":
    "Zoom, pan, fit view, busca, filtros, seleção, agrupamento e destaque de caminho",
  "pages.evidenceGraph.planned.3":
    "Alternativa textual acessível para todas as relações do grafo",
  "pages.evidenceGraph.planned.4":
    "Seleção de hipótese destaca todas as evidências associadas",

  "pages.workloads.title": "Workloads — Glue & EMR",
  "pages.workloads.lead":
    "Investigação operacional dos motores AWS suportados: jobs Glue e clusters EMR.",
  "pages.workloads.planned.0":
    "Glue: job, run ID, status, runtime, início/fim, duração, erros, métricas e findings",
  "pages.workloads.planned.1":
    "EMR on EC2: clusters, steps e artefatos exportados quando disponíveis",
  "pages.workloads.planned.2":
    "Somente fontes offline/exportadas até existir conector online funcional",

  "pages.sparkPlans.title": "Planos Spark",
  "pages.sparkPlans.lead":
    "Explorador de planos de execução Spark (EXPLAIN) com árvore de operadores e métricas de custo.",
  "pages.sparkPlans.planned.0":
    "Árvore de operadores do plano físico e lógico",
  "pages.sparkPlans.planned.1":
    "Métricas de custo, shuffle, skew e estágios",
  "pages.sparkPlans.planned.2":
    "Comparação de planos quando múltiplos artefatos estiverem disponíveis",

  "pages.qualityLineage.title": "Qualidade e linhagem",
  "pages.qualityLineage.lead":
    "Observações de qualidade de dados e linhagem via eventos OpenLineage.",
  "pages.qualityLineage.planned.0":
    "Observações de qualidade associadas a datasets e runs",
  "pages.qualityLineage.planned.1":
    "Linhagem dataset→dataset a partir de eventos OpenLineage importados",
  "pages.qualityLineage.planned.2":
    "Ligação entre violações de qualidade e findings da investigação",

  "pages.agents.title": "Agentes",
  "pages.agents.lead":
    "Catálogo de agentes especializados determinísticos e ferramentas registradas.",
  "pages.agents.planned.0":
    "Descritores de agentes (GET /api/v1/agents): responsabilidade, ferramentas permitidas e limites",
  "pages.agents.planned.1":
    "Manifesto de ferramentas (GET /api/v1/tools) com schemas de entrada",
  "pages.agents.planned.2":
    "Atividade de agentes por investigação quando o stream estiver disponível",

  "pages.reports.title": "Relatórios",
  "pages.reports.lead":
    "Relatórios de investigação concluídos com findings, evidências e proveniência.",
  "pages.reports.planned.0":
    "Listagem de investigações concluídas (GET /api/v1/investigations)",
  "pages.reports.planned.1":
    "Relatório completo: findings, hipóteses, conclusões, recomendações e limitações",
  "pages.reports.planned.2":
    "Exportação do relatório preservando proveniência",

  "api.error.unreachable":
    "Não foi possível alcançar a API em 127.0.0.1:8790. Verifique se o backend está em execução.",
  "api.error.server": "Erro interno da API.",
  "api.error.notFound": "Recurso não encontrado na API.",
  "api.error.request": "A API rejeitou a requisição.",
  "api.error.unknown": "Erro desconhecido ao falar com a API.",
};

export const EN: TranslationDict = {
  "app.name": "Data Sentinel",
  "app.subtitle": "Control Center",

  "a11y.skipToContent": "Skip to content",
  "a11y.primaryNav": "Primary navigation",
  "a11y.topbar": "Top bar",
  "a11y.notifications": "Notifications",
  "a11y.dismiss": "Dismiss notification",

  "nav.dashboard": "Overview",
  "nav.investigations": "Investigations",
  "nav.evidenceGraph": "Evidence Graph",
  "nav.workloads": "Workloads",
  "nav.sparkPlans": "Spark Plans",
  "nav.qualityLineage": "Quality & Lineage",
  "nav.agents": "Agents",
  "nav.reports": "Reports",

  "theme.toLight": "Switch to light theme",
  "theme.toDark": "Switch to dark theme",
  "lang.switch": "Mudar para português",

  "status.underConstruction": "Under construction",
  "status.plannedCapabilities": "Planned capabilities",
  "status.apiConnected": "API connected",
  "status.apiUnreachable": "API unreachable",
  "status.loading": "Loading…",
  "status.retry": "Retry",

  "pages.dashboard.title": "Overview",
  "pages.dashboard.lead":
    "Data Sentinel platform and Control Center API status.",
  "pages.dashboard.apiCard.title": "Control Center API",
  "pages.dashboard.apiCard.version": "Core version",
  "pages.dashboard.apiCard.api": "API version",
  "pages.dashboard.apiCard.endpoint": "Endpoint",
  "pages.dashboard.apiCard.hint":
    "Start the API with `sentinel-api` (uvicorn on 127.0.0.1:8790) to connect.",
  "pages.dashboard.capsCard.title": "Registered capabilities",
  "pages.dashboard.capsCard.caps": "capabilities",
  "pages.dashboard.capsCard.tools": "tools",
  "pages.dashboard.capsCard.agents": "specialist agents",
  "pages.dashboard.capsCard.empty": "No data — the API has not responded yet.",
  "pages.dashboard.scope.title": "Scope of this release",
  "pages.dashboard.scope.body":
    "Angular foundation + design system. Investigation, evidence graph, workloads, Spark plans, quality, agents and reports studios are mapped as minimal real routes and will be implemented in upcoming phases — no functionality is simulated.",

  "pages.investigations.title": "Investigations",
  "pages.investigations.lead":
    "Primary workspace: start and track diagnostic investigations with evidence, hypotheses and recommendations.",
  "pages.investigations.planned.0":
    "Source selection (Glue Job Run, EMR artifacts, SQL, Spark EXPLAIN, CloudWatch logs, Iceberg, quality observations, OpenLineage events, doctor bundle)",
  "pages.investigations.planned.1":
    "Investigation profiles and required-permission preview",
  "pages.investigations.planned.2": "Progress tracking via event stream (SSE)",
  "pages.investigations.planned.3":
    "Panels: summary, agent activity, findings, evidence, hypotheses, timeline and recommendations",
  "pages.investigations.planned.4":
    "Evidence inspector with source, provenance, hash, confidence and limitations",
  "pages.investigations.planned.5": "Report export",

  "pages.evidenceGraph.title": "Evidence Graph",
  "pages.evidenceGraph.lead":
    "Evidence graph explorer: nodes, relations and paths across jobs, datasets, findings and hypotheses.",
  "pages.evidenceGraph.planned.0":
    "Nodes: Job, Run, Dataset, Spark Stage, Log Event, Evidence, Finding, Hypothesis, Agent, Tool, Iceberg Snapshot, Quality Observation",
  "pages.evidenceGraph.planned.1":
    "Edges: READS, WRITES, PRODUCES, DEPENDS_ON, SUPPORTED_BY, ASSOCIATED_WITH, POTENTIALLY_CAUSED_BY, VALIDATED_BY",
  "pages.evidenceGraph.planned.2":
    "Zoom, pan, fit view, search, filters, selection, grouping and path highlight",
  "pages.evidenceGraph.planned.3":
    "Accessible textual alternative for all graph relations",
  "pages.evidenceGraph.planned.4":
    "Selecting a hypothesis highlights all associated evidence",

  "pages.workloads.title": "Workloads — Glue & EMR",
  "pages.workloads.lead":
    "Operational investigation for supported AWS engines: Glue jobs and EMR clusters.",
  "pages.workloads.planned.0":
    "Glue: job, run ID, status, runtime, start/end, duration, errors, metrics and findings",
  "pages.workloads.planned.1":
    "EMR on EC2: clusters, steps and exported artifacts when available",
  "pages.workloads.planned.2":
    "Offline/exported sources only until a working online connector exists",

  "pages.sparkPlans.title": "Spark Plans",
  "pages.sparkPlans.lead":
    "Spark execution plan explorer (EXPLAIN) with operator tree and cost metrics.",
  "pages.sparkPlans.planned.0": "Physical and logical plan operator tree",
  "pages.sparkPlans.planned.1": "Cost, shuffle, skew and stage metrics",
  "pages.sparkPlans.planned.2":
    "Plan comparison when multiple artifacts are available",

  "pages.qualityLineage.title": "Quality & Lineage",
  "pages.qualityLineage.lead":
    "Data quality observations and lineage from OpenLineage events.",
  "pages.qualityLineage.planned.0":
    "Quality observations linked to datasets and runs",
  "pages.qualityLineage.planned.1":
    "Dataset-to-dataset lineage from imported OpenLineage events",
  "pages.qualityLineage.planned.2":
    "Link between quality violations and investigation findings",

  "pages.agents.title": "Agents",
  "pages.agents.lead":
    "Catalog of deterministic specialist agents and registered tools.",
  "pages.agents.planned.0":
    "Agent descriptors (GET /api/v1/agents): responsibility, allowed tools and limits",
  "pages.agents.planned.1":
    "Tool manifest (GET /api/v1/tools) with input schemas",
  "pages.agents.planned.2":
    "Per-investigation agent activity once the stream is available",

  "pages.reports.title": "Reports",
  "pages.reports.lead":
    "Completed investigation reports with findings, evidence and provenance.",
  "pages.reports.planned.0":
    "List of completed investigations (GET /api/v1/investigations)",
  "pages.reports.planned.1":
    "Full report: findings, hypotheses, conclusions, recommendations and limitations",
  "pages.reports.planned.2": "Report export preserving provenance",

  "api.error.unreachable":
    "Could not reach the API at 127.0.0.1:8790. Check that the backend is running.",
  "api.error.server": "Internal API error.",
  "api.error.notFound": "Resource not found on the API.",
  "api.error.request": "The API rejected the request.",
  "api.error.unknown": "Unknown error while contacting the API.",
};
