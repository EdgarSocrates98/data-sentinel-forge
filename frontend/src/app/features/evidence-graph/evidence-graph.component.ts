import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from "@angular/core";
import { ActivatedRoute, RouterLink } from "@angular/router";

import {
  Evidence,
  Finding,
  Hypothesis,
  InvestigationReport,
  InvestigationSummary,
  isInvestigationReport,
} from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { confidenceClass, severityClass } from "../../shared/status-class";
import {
  GraphModel,
  GraphNode,
  buildInvestigationGraph,
} from "./evidence-graph.model";
import { GraphCanvasComponent } from "./graph-canvas.component";

type ListState = "loading" | "ok" | "error";
type ReportState = "idle" | "loading" | "ok" | "running" | "error";

/**
 * Evidence Graph Explorer (ds-0074 §6): interactive SVG graph of the
 * relations inside a real investigation report (findings → evidence →
 * hypotheses). The API exposes no graph endpoint yet, so the model is
 * derived client-side by `buildInvestigationGraph` from real payload
 * references only; gaps are declared, never simulated.
 */
@Component({
  selector: "ds-evidence-graph",
  standalone: true,
  imports: [RouterLink, TranslatePipe, GraphCanvasComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./evidence-graph.component.html",
  styleUrl: "./evidence-graph.component.css",
})
export class EvidenceGraphComponent {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);

  protected readonly severityClass = severityClass;
  protected readonly confidenceClass = confidenceClass;

  protected readonly listState = signal<ListState>("loading");
  protected readonly investigations = signal<InvestigationSummary[]>([]);
  protected readonly selectedInvestigation = signal("");
  protected readonly reportState = signal<ReportState>("idle");
  protected readonly report = signal<InvestigationReport | null>(null);
  protected readonly query = signal("");
  protected readonly selectedNodeId = signal<string | null>(null);

  protected readonly graph = computed<GraphModel | null>(() => {
    const rep = this.report();
    return rep ? buildInvestigationGraph(rep) : null;
  });

  protected readonly selectedNode = computed<GraphNode | null>(() => {
    const id = this.selectedNodeId();
    return this.graph()?.nodes.find((n) => n.id === id) ?? null;
  });

  constructor() {
    this.loadList();
    // Deep link: /evidence-graph?investigation=<id>
    const preset = this.route.snapshot.queryParamMap.get("investigation");
    if (preset) {
      this.selectedInvestigation.set(preset);
      this.loadReport();
    }
  }

  protected loadList(): void {
    this.listState.set("loading");
    this.api.listInvestigations().subscribe({
      next: (items) => {
        this.investigations.set(items);
        this.listState.set("ok");
      },
      error: () => {
        this.investigations.set([]);
        this.listState.set("error");
      },
    });
  }

  protected onPick(id: string): void {
    this.selectedInvestigation.set(id);
    this.loadReport();
  }

  protected loadReport(): void {
    const id = this.selectedInvestigation();
    if (!id) {
      this.report.set(null);
      this.reportState.set("idle");
      return;
    }
    this.reportState.set("loading");
    this.report.set(null);
    this.selectedNodeId.set(null);
    this.api.getInvestigation(id).subscribe({
      next: (detail) => {
        if (isInvestigationReport(detail)) {
          this.report.set(detail);
          this.reportState.set("ok");
        } else {
          this.reportState.set("running");
        }
      },
      error: () => this.reportState.set("error"),
    });
  }

  protected onNodeSelected(id: string): void {
    this.selectedNodeId.set(this.selectedNodeId() === id ? null : id);
  }

  protected onSearch(value: string): void {
    this.query.set(value);
  }

  // ---- detail-panel type guards over the real payloads ----

  protected asFinding(node: GraphNode): Finding | null {
    return node.kind === "finding" ? (node.data as Finding) : null;
  }

  protected asEvidence(node: GraphNode): Evidence | null {
    return node.kind === "evidence" && !node.referencedOnly
      ? (node.data as Evidence)
      : null;
  }

  protected asHypothesis(node: GraphNode): Hypothesis | null {
    return node.kind === "hypothesis" ? (node.data as Hypothesis) : null;
  }

  protected asReport(node: GraphNode): InvestigationReport | null {
    return node.kind === "investigation"
      ? (node.data as InvestigationReport)
      : null;
  }

  /** Node kind → i18n label key. */
  protected kindLabelKey(kind: GraphNode["kind"]): string {
    return `graph.kind.${kind}`;
  }
}
