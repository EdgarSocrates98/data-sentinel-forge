import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from "@angular/core";
import { RouterLink } from "@angular/router";
import { forkJoin } from "rxjs";

import {
  isInvestigationReport,
  type AgentDescriptor,
  type InvestigationReport,
  type InvestigationSummary,
  type ToolManifestEntry,
} from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";

type LoadState = "loading" | "ok" | "error";

/**
 * Agent Operations Center (ds-0076, spec 06.8): the real specialist
 * registry (GET /api/v1/agents) with declared tools, policy and
 * limits; the tool manifest (GET /api/v1/tools); and per-investigation
 * agent/tool/token activity read from completed reports. Token and
 * cost values are reported verbatim — no gauges, no estimates.
 */
@Component({
  selector: "ds-agents",
  standalone: true,
  imports: [RouterLink, TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./agents.component.html",
  styleUrl: "./agents.component.css",
})
export class AgentsComponent {
  private readonly api = inject(ApiService);

  protected readonly state = signal<LoadState>("loading");
  protected readonly agents = signal<AgentDescriptor[]>([]);
  protected readonly tools = signal<ToolManifestEntry[]>([]);

  protected readonly invState = signal<LoadState>("loading");
  protected readonly investigations = signal<InvestigationSummary[]>([]);
  protected readonly selectedInv = signal("");
  protected readonly reportState = signal<LoadState | "idle">("idle");
  protected readonly report = signal<InvestigationReport | null>(null);

  /** Agents sorted by id for a deterministic table. */
  protected readonly sortedAgents = computed(() =>
    [...this.agents()].sort((a, b) => a.agent_id.localeCompare(b.agent_id)),
  );

  constructor() {
    this.load();
  }

  protected load(): void {
    this.state.set("loading");
    forkJoin({
      agents: this.api.agents(),
      tools: this.api.tools(),
      investigations: this.api.listInvestigations(),
    }).subscribe({
      next: (res) => {
        this.agents.set(res.agents);
        this.tools.set(res.tools);
        this.investigations.set(res.investigations);
        this.state.set("ok");
        this.invState.set("ok");
      },
      error: () => {
        this.agents.set([]);
        this.tools.set([]);
        this.investigations.set([]);
        this.state.set("error");
        this.invState.set("error");
      },
    });
  }

  protected selectInvestigation(id: string): void {
    this.selectedInv.set(id);
    this.report.set(null);
    if (!id) {
      this.reportState.set("idle");
      return;
    }
    this.reportState.set("loading");
    this.api.getInvestigation(id).subscribe({
      next: (detail) => {
        if (isInvestigationReport(detail)) {
          this.report.set(detail);
          this.reportState.set("ok");
        } else {
          this.report.set(null);
          this.reportState.set("idle");
        }
      },
      error: () => {
        this.report.set(null);
        this.reportState.set("error");
      },
    });
  }
}
