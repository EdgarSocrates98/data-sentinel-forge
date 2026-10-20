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

  "investigations.new.action": "Nova investigação",
  "investigations.open": "Abrir",
  "investigations.list.title": "Investigações registradas",
  "investigations.list.error":
    "Não foi possível carregar a lista de investigações.",
  "investigations.list.empty.title": "Nenhuma investigação ainda",
  "investigations.list.empty.body":
    "A API está online, mas nenhuma investigação foi concluída neste processo. Inicie a primeira.",
  "investigations.col.id": "ID",
  "investigations.col.status": "Status",
  "investigations.col.created": "Criada em",
  "investigations.col.open": "Abrir investigação",
  "investigations.col.severity": "Severidade",
  "investigations.col.category": "Categoria",
  "investigations.col.explanation": "Explicação",
  "investigations.col.evidence": "Evidências",
  "investigations.status.running": "Em execução",
  "investigations.status.completed": "Concluída",
  "investigations.status.failed": "Falhou",

  "investigations.new.title": "Nova investigação",
  "investigations.new.lead":
    "Descreva o problema e anexe artefatos locais vinculados a ferramentas reais do registro.",
  "investigations.new.hint":
    "Somente ferramentas que aceitam um único arquivo (`file`) são elegíveis — o endpoint executa pares {tool_id: path}.",
  "investigations.new.problem": "Problema a investigar",
  "investigations.new.problemRequired":
    "Descreva o problema (1–4000 caracteres).",
  "investigations.new.files": "Artefatos de entrada",
  "investigations.new.filesHint":
    "Caminhos locais acessíveis ao processo da API (extensões permitidas: .json .log .txt .sql .yaml .plan .xml .csv .jsonl).",
  "investigations.new.tool": "Ferramenta",
  "investigations.new.toolPlaceholder": "Selecione a ferramenta",
  "investigations.new.path": "Caminho do arquivo",
  "investigations.new.addFile": "Adicionar artefato",
  "investigations.new.removeFile": "Remover artefato",
  "investigations.new.duplicateTool":
    "A mesma ferramenta foi selecionada mais de uma vez — cada tool_id aceita um único arquivo.",
  "investigations.new.submit": "Iniciar investigação",
  "investigations.new.submitting": "Iniciando…",
  "investigations.new.cancel": "Cancelar",
  "investigations.new.toolsError":
    "Não foi possível carregar o registro de ferramentas.",
  "investigations.new.noFileTools":
    "Nenhuma ferramenta baseada em arquivo disponível no registro.",

  "investigations.detail.back": "Voltar às investigações",
  "investigations.detail.title": "Investigação",
  "investigations.detail.summary": "Resumo da investigação",
  "investigations.detail.progress": "Progresso ao vivo",
  "investigations.detail.progressHint":
    "Eventos recebidos via stream SSE enquanto a investigação executa.",
  "investigations.detail.streamError":
    "A conexão com o stream de eventos caiu — o relatório pode estar pronto; tente atualizar.",
  "investigations.detail.noEvents": "Aguardando eventos…",
  "investigations.detail.failed": "A investigação falhou",
  "investigations.detail.failedHint":
    "O backend registrou a falha; nenhum relatório foi produzido.",
  "investigations.detail.notFound": "Investigação não encontrada",
  "investigations.detail.notFoundHint":
    "O id não existe neste processo da API — investigações são mantidas em memória e somem ao reiniciar o backend.",
  "investigations.detail.errorHint":
    "Não foi possível carregar esta investigação.",
  "investigations.detail.openGraph": "Ver no grafo",
  "investigations.detail.export": "Exportar JSON",
  "investigations.detail.tokens": "Tokens usados",
  "investigations.detail.duration": "Duração",
  "investigations.detail.cost": "Custo (USD)",
  "investigations.detail.activity": "Atividade de agentes e ferramentas",
  "investigations.detail.agentsUsed": "Agentes utilizados",
  "investigations.detail.toolsUsed": "Ferramentas utilizadas",
  "investigations.detail.none": "Nenhum registro.",
  "investigations.detail.toolOk": "ok",
  "investigations.detail.toolFailed": "falhou",
  "investigations.detail.validation": "Validação independente",
  "investigations.detail.validationChecked": "Findings verificados",
  "investigations.detail.findings": "Findings",
  "investigations.detail.noFindings":
    "Nenhum finding produzido por esta investigação.",
  "investigations.detail.expand": "Expandir",
  "investigations.detail.collapse": "Recolher",
  "investigations.detail.evidenceIds": "IDs de evidência",
  "investigations.detail.findingRecs": "Recomendações do finding",
  "investigations.detail.validationSteps": "Passos de validação",
  "investigations.detail.alternatives": "Alternativas",
  "investigations.detail.hypotheses": "Hipóteses",
  "investigations.detail.causalNote":
    "Hipóteses são correlações rotuladas (causal_label) — um score numérico nunca é apresentado como causalidade confirmada.",
  "investigations.detail.hypSupported": "Suportadas",
  "investigations.detail.hypRefuted": "Refutadas",
  "investigations.detail.supportingEvidence": "Evidências de suporte",
  "investigations.detail.contradictingEvidence": "Evidências contraditórias",
  "investigations.detail.evidence": "Evidências",
  "investigations.detail.noEvidence":
    "O relatório não carrega payloads de evidência — findings podem referenciar evidence_ids não incluídos.",
  "investigations.detail.conclusions": "Conclusões",
  "investigations.detail.recommendations": "Recomendações",
  "investigations.detail.limitations": "Limitações",

  "investigations.ev.sourceLocation": "Local de origem",
  "investigations.ev.capturedAt": "Capturada em",
  "investigations.ev.hash": "Hash do conteúdo",
  "investigations.ev.provenance": "Proveniência",
  "investigations.ev.access": "Metadados de acesso",

  "investigations.rec.expected": "Efeito esperado",
  "investigations.rec.risk": "Risco estimado",
  "investigations.rec.validation": "Plano de validação",
  "investigations.rec.rollback": "Plano de rollback",

  "pages.evidenceGraph.title": "Grafo de evidências",
  "pages.evidenceGraph.lead":
    "Explorador do grafo de evidências: nós, relações e caminhos entre findings, evidências e hipóteses de uma investigação real.",

  "graph.picker.title": "Investigação",
  "graph.picker.label": "Selecionar investigação",
  "graph.picker.placeholder": "Escolha uma investigação concluída",
  "graph.picker.hint":
    "Escolha uma investigação para derivar o grafo a partir do relatório real.",
  "graph.picker.empty":
    "Nenhuma investigação disponível — inicie uma no Investigation Studio.",
  "graph.picker.error": "Não foi possível listar as investigações.",
  "graph.running":
    "Esta investigação ainda está em execução — o grafo fica disponível quando o relatório existir.",
  "graph.openInvestigation": "Abrir investigação",
  "graph.loadError": "Não foi possível carregar o relatório.",
  "graph.title": "Grafo derivado do relatório",
  "graph.searchLabel": "Filtrar nós",
  "graph.searchPlaceholder": "Filtrar por id, rótulo ou tipo…",
  "graph.stats": "Totais",
  "graph.statsNodes": "nós",
  "graph.statsEdges": "arestas",
  "graph.limitations": "Limitações do grafo",
  "graph.toolbar": "Controles do grafo",
  "graph.zoomIn": "Ampliar",
  "graph.zoomOut": "Reduzir",
  "graph.fit": "Ajustar à tela",
  "graph.canvasLabel":
    "Grafo de evidências — use as tabelas abaixo para uma descrição textual completa",
  "graph.detail.title": "Detalhes do nó",
  "graph.detail.empty": "Selecione um nó no grafo para ver seus dados.",
  "graph.detail.referencedOnly":
    "Este evidence_id é referenciado pelo relatório, mas o payload completo da evidência não está incluído nele — nó de referência, sem conteúdo adicional.",
  "graph.detail.confidence": "Confiança",
  "graph.detail.causalLabel": "Rótulo causal",
  "graph.detail.statement": "Declaração",
  "graph.kind.investigation": "Investigação",
  "graph.kind.finding": "Finding",
  "graph.kind.evidence": "Evidência",
  "graph.kind.hypothesis": "Hipótese",
  "graph.kind.tool": "Ferramenta",
  "graph.kind.agent": "Agente",
  "graph.a11y.title": "Descrição textual do grafo",
  "graph.a11y.hint":
    "Equivalente acessível: todos os nós e relações renderizados acima, em formato tabular.",
  "graph.a11y.nodes": "Nós",
  "graph.a11y.edges": "Arestas",
  "graph.a11y.colNode": "Id do nó",
  "graph.a11y.colKind": "Tipo",
  "graph.a11y.colLabel": "Rótulo",
  "graph.a11y.colFrom": "Origem",
  "graph.a11y.colRel": "Relação",
  "graph.a11y.colTo": "Destino",
  "graph.a11y.colJust": "Justificativa",
  "graph.a11y.noEdges": "Nenhuma aresta — o relatório não contém relações.",

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

  "investigations.new.action": "New investigation",
  "investigations.open": "Open",
  "investigations.list.title": "Recorded investigations",
  "investigations.list.error": "Could not load the investigation list.",
  "investigations.list.empty.title": "No investigations yet",
  "investigations.list.empty.body":
    "The API is online but no investigation has completed in this process. Start the first one.",
  "investigations.col.id": "ID",
  "investigations.col.status": "Status",
  "investigations.col.created": "Created",
  "investigations.col.open": "Open investigation",
  "investigations.col.severity": "Severity",
  "investigations.col.category": "Category",
  "investigations.col.explanation": "Explanation",
  "investigations.col.evidence": "Evidence",
  "investigations.status.running": "Running",
  "investigations.status.completed": "Completed",
  "investigations.status.failed": "Failed",

  "investigations.new.title": "New investigation",
  "investigations.new.lead":
    "Describe the problem and attach local artifacts bound to real registry tools.",
  "investigations.new.hint":
    "Only tools that accept a single `file` input are eligible — the endpoint executes {tool_id: path} pairs.",
  "investigations.new.problem": "Problem to investigate",
  "investigations.new.problemRequired":
    "Describe the problem (1–4000 characters).",
  "investigations.new.files": "Input artifacts",
  "investigations.new.filesHint":
    "Local paths readable by the API process (allowed extensions: .json .log .txt .sql .yaml .plan .xml .csv .jsonl).",
  "investigations.new.tool": "Tool",
  "investigations.new.toolPlaceholder": "Select a tool",
  "investigations.new.path": "File path",
  "investigations.new.addFile": "Add artifact",
  "investigations.new.removeFile": "Remove artifact",
  "investigations.new.duplicateTool":
    "The same tool was selected more than once — each tool_id accepts a single file.",
  "investigations.new.submit": "Start investigation",
  "investigations.new.submitting": "Starting…",
  "investigations.new.cancel": "Cancel",
  "investigations.new.toolsError": "Could not load the tool registry.",
  "investigations.new.noFileTools":
    "No file-based tool available in the registry.",

  "investigations.detail.back": "Back to investigations",
  "investigations.detail.title": "Investigation",
  "investigations.detail.summary": "Investigation summary",
  "investigations.detail.progress": "Live progress",
  "investigations.detail.progressHint":
    "Events received over the SSE stream while the investigation runs.",
  "investigations.detail.streamError":
    "The event stream connection dropped — the report may be ready; try refreshing.",
  "investigations.detail.noEvents": "Waiting for events…",
  "investigations.detail.failed": "The investigation failed",
  "investigations.detail.failedHint":
    "The backend recorded the failure; no report was produced.",
  "investigations.detail.notFound": "Investigation not found",
  "investigations.detail.notFoundHint":
    "This id does not exist in the current API process — investigations are held in memory and disappear when the backend restarts.",
  "investigations.detail.errorHint": "Could not load this investigation.",
  "investigations.detail.openGraph": "View in graph",
  "investigations.detail.export": "Export JSON",
  "investigations.detail.tokens": "Tokens used",
  "investigations.detail.duration": "Duration",
  "investigations.detail.cost": "Cost (USD)",
  "investigations.detail.activity": "Agent & tool activity",
  "investigations.detail.agentsUsed": "Agents used",
  "investigations.detail.toolsUsed": "Tools used",
  "investigations.detail.none": "No records.",
  "investigations.detail.toolOk": "ok",
  "investigations.detail.toolFailed": "failed",
  "investigations.detail.validation": "Independent validation",
  "investigations.detail.validationChecked": "Findings checked",
  "investigations.detail.findings": "Findings",
  "investigations.detail.noFindings":
    "This investigation produced no findings.",
  "investigations.detail.expand": "Expand",
  "investigations.detail.collapse": "Collapse",
  "investigations.detail.evidenceIds": "Evidence ids",
  "investigations.detail.findingRecs": "Finding recommendations",
  "investigations.detail.validationSteps": "Validation steps",
  "investigations.detail.alternatives": "Alternatives",
  "investigations.detail.hypotheses": "Hypotheses",
  "investigations.detail.causalNote":
    "Hypotheses are labeled correlations (causal_label) — a numeric score is never presented as confirmed causality.",
  "investigations.detail.hypSupported": "Supported",
  "investigations.detail.hypRefuted": "Refuted",
  "investigations.detail.supportingEvidence": "Supporting evidence",
  "investigations.detail.contradictingEvidence": "Contradicting evidence",
  "investigations.detail.evidence": "Evidence",
  "investigations.detail.noEvidence":
    "The report carries no evidence payloads — findings may reference evidence_ids not included.",
  "investigations.detail.conclusions": "Conclusions",
  "investigations.detail.recommendations": "Recommendations",
  "investigations.detail.limitations": "Limitations",

  "investigations.ev.sourceLocation": "Source location",
  "investigations.ev.capturedAt": "Captured at",
  "investigations.ev.hash": "Content hash",
  "investigations.ev.provenance": "Provenance",
  "investigations.ev.access": "Access metadata",

  "investigations.rec.expected": "Expected effect",
  "investigations.rec.risk": "Estimated risk",
  "investigations.rec.validation": "Validation plan",
  "investigations.rec.rollback": "Rollback plan",

  "pages.evidenceGraph.title": "Evidence Graph",
  "pages.evidenceGraph.lead":
    "Evidence graph explorer: nodes, relations and paths across the findings, evidence and hypotheses of a real investigation.",

  "graph.picker.title": "Investigation",
  "graph.picker.label": "Select investigation",
  "graph.picker.placeholder": "Choose a completed investigation",
  "graph.picker.hint":
    "Pick an investigation to derive the graph from its real report.",
  "graph.picker.empty":
    "No investigations available — start one in the Investigation Studio.",
  "graph.picker.error": "Could not list investigations.",
  "graph.running":
    "This investigation is still running — the graph becomes available once a report exists.",
  "graph.openInvestigation": "Open investigation",
  "graph.loadError": "Could not load the report.",
  "graph.title": "Graph derived from report",
  "graph.searchLabel": "Filter nodes",
  "graph.searchPlaceholder": "Filter by id, label or kind…",
  "graph.stats": "Totals",
  "graph.statsNodes": "nodes",
  "graph.statsEdges": "edges",
  "graph.limitations": "Graph limitations",
  "graph.toolbar": "Graph controls",
  "graph.zoomIn": "Zoom in",
  "graph.zoomOut": "Zoom out",
  "graph.fit": "Fit to view",
  "graph.canvasLabel":
    "Evidence graph — use the tables below for a full textual description",
  "graph.detail.title": "Node details",
  "graph.detail.empty": "Select a node in the graph to inspect its data.",
  "graph.detail.referencedOnly":
    "This evidence_id is referenced by the report, but its full evidence payload is not included — reference node, no further content.",
  "graph.detail.confidence": "Confidence",
  "graph.detail.causalLabel": "Causal label",
  "graph.detail.statement": "Statement",
  "graph.kind.investigation": "Investigation",
  "graph.kind.finding": "Finding",
  "graph.kind.evidence": "Evidence",
  "graph.kind.hypothesis": "Hypothesis",
  "graph.kind.tool": "Tool",
  "graph.kind.agent": "Agent",
  "graph.a11y.title": "Textual description of the graph",
  "graph.a11y.hint":
    "Accessible equivalent: every node and relation rendered above, in tabular form.",
  "graph.a11y.nodes": "Nodes",
  "graph.a11y.edges": "Edges",
  "graph.a11y.colNode": "Node id",
  "graph.a11y.colKind": "Kind",
  "graph.a11y.colLabel": "Label",
  "graph.a11y.colFrom": "From",
  "graph.a11y.colRel": "Relation",
  "graph.a11y.colTo": "To",
  "graph.a11y.colJust": "Justification",
  "graph.a11y.noEdges": "No edges — the report contains no relations.",

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
