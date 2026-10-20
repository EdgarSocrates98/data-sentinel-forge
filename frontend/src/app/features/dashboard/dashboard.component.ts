import { ChangeDetectionStrategy, Component, inject, signal } from "@angular/core";
import { forkJoin } from "rxjs";

import { environment } from "../../../environments/environment";
import type { HealthResponse } from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";

type LoadState = "loading" | "ok" | "error";

/**
 * Overview page — real connectivity probe against the Control Center
 * API (health + capability/tool/agent counts). No simulated data.
 */
@Component({
  selector: "ds-dashboard",
  standalone: true,
  imports: [TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./dashboard.component.html",
  styleUrl: "./dashboard.component.css",
})
export class DashboardComponent {
  private readonly api = inject(ApiService);

  protected readonly state = signal<LoadState>("loading");
  protected readonly health = signal<HealthResponse | null>(null);
  protected readonly counts = signal<{
    capabilities: number;
    tools: number;
    agents: number;
  } | null>(null);
  protected readonly endpoint = environment.apiBaseUrl;

  constructor() {
    this.refresh();
  }

  protected refresh(): void {
    this.state.set("loading");
    forkJoin({
      health: this.api.health(),
      capabilities: this.api.capabilities(),
      tools: this.api.tools(),
      agents: this.api.agents(),
    }).subscribe({
      next: (res) => {
        this.health.set(res.health);
        this.counts.set({
          capabilities: res.capabilities.length,
          tools: res.tools.length,
          agents: res.agents.length,
        });
        this.state.set("ok");
      },
      error: () => {
        this.health.set(null);
        this.counts.set(null);
        this.state.set("error");
      },
    });
  }
}
