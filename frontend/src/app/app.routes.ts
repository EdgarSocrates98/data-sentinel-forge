import { Routes } from "@angular/router";

import { authGuard, sessionGateGuard } from "./core/session/auth.guard";

/**
 * Lazy-loaded feature routes. `title` carries an i18n key resolved by
 * `LocalizedTitleStrategy`; nav labels use `data.labelKey`.
 *
 * `/session` is the onboarding gate (ds-0101 / ADR-0014) and is the only
 * unguarded route; every other route requires `authGuard`.
 */
export const routes: Routes = [
  {
    path: "session",
    title: "session.gate.title",
    canActivate: [sessionGateGuard],
    loadComponent: () =>
      import("./features/session-gate/session-gate.component").then(
        (m) => m.SessionGateComponent,
      ),
  },
  {
    path: "",
    title: "pages.dashboard.title",
    data: { labelKey: "nav.dashboard" },
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/dashboard/dashboard.component").then(
        (m) => m.DashboardComponent,
      ),
  },
  {
    path: "investigations",
    title: "pages.investigations.title",
    data: { labelKey: "nav.investigations" },
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/investigations/investigations.component").then(
        (m) => m.InvestigationsComponent,
      ),
  },
  {
    path: "investigations/new",
    title: "investigations.new.title",
    data: { labelKey: "nav.investigations" },
    canActivate: [authGuard],
    loadComponent: () =>
      import(
        "./features/investigations/investigation-new.component"
      ).then((m) => m.InvestigationNewComponent),
  },
  {
    path: "investigations/:id",
    title: "investigations.detail.title",
    data: { labelKey: "nav.investigations" },
    canActivate: [authGuard],
    loadComponent: () =>
      import(
        "./features/investigations/investigation-detail.component"
      ).then((m) => m.InvestigationDetailComponent),
  },
  {
    path: "evidence-graph",
    title: "pages.evidenceGraph.title",
    data: { labelKey: "nav.evidenceGraph" },
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/evidence-graph/evidence-graph.component").then(
        (m) => m.EvidenceGraphComponent,
      ),
  },
  {
    path: "workloads",
    title: "pages.workloads.title",
    data: { labelKey: "nav.workloads" },
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/workloads/workloads.component").then(
        (m) => m.WorkloadsComponent,
      ),
  },
  {
    path: "spark-plans",
    title: "pages.sparkPlans.title",
    data: { labelKey: "nav.sparkPlans" },
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/spark-plans/spark-plans.component").then(
        (m) => m.SparkPlansComponent,
      ),
  },
  {
    path: "quality-lineage",
    title: "pages.qualityLineage.title",
    data: { labelKey: "nav.qualityLineage" },
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/quality-lineage/quality-lineage.component").then(
        (m) => m.QualityLineageComponent,
      ),
  },
  {
    path: "agents",
    title: "pages.agents.title",
    data: { labelKey: "nav.agents" },
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/agents/agents.component").then(
        (m) => m.AgentsComponent,
      ),
  },
  {
    path: "reports",
    title: "pages.reports.title",
    data: { labelKey: "nav.reports" },
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/reports/reports.component").then(
        (m) => m.ReportsComponent,
      ),
  },
  {
    path: "operations",
    title: "pages.operations.title",
    data: { labelKey: "nav.operations" },
    canActivate: [authGuard],
    loadComponent: () =>
      import(
        "./features/operations/operations-dashboard.component"
      ).then((m) => m.OperationsDashboardComponent),
  },
  {
    path: "operations/timeline",
    title: "pages.opsTimeline.title",
    data: { labelKey: "nav.operations" },
    canActivate: [authGuard],
    loadComponent: () =>
      import(
        "./features/operations/workload-timeline.component"
      ).then((m) => m.WorkloadTimelineComponent),
  },
  {
    path: "operations/regressions",
    title: "pages.opsRegressions.title",
    data: { labelKey: "nav.operations" },
    canActivate: [authGuard],
    loadComponent: () =>
      import(
        "./features/operations/regression-explorer.component"
      ).then((m) => m.RegressionExplorerComponent),
  },
  {
    path: "operations/watches",
    title: "pages.opsWatches.title",
    data: { labelKey: "nav.operations" },
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/operations/watch-center.component").then(
        (m) => m.WatchCenterComponent,
      ),
  },
  {
    path: "operations/remediation",
    title: "pages.opsRemediation.title",
    data: { labelKey: "nav.operations" },
    canActivate: [authGuard],
    loadComponent: () =>
      import(
        "./features/operations/remediation-workspace.component"
      ).then((m) => m.RemediationWorkspaceComponent),
  },
  { path: "**", redirectTo: "" },
];
