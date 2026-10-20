import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from "@angular/core";
import { RouterLink } from "@angular/router";

import type { InvestigationSummary } from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { I18nService } from "../../core/i18n/i18n.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { statusClass } from "../../shared/status-class";

type LoadState = "loading" | "ok" | "error";

/**
 * Investigation Studio — list of investigations recorded by the
 * Control Center API (GET /api/v1/investigations). Real data only;
 * empty/error states are explicit. Entry point to the new-investigation
 * form and to each investigation detail workspace.
 */
@Component({
  selector: "ds-investigations",
  standalone: true,
  imports: [RouterLink, TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./investigations.component.html",
  styleUrl: "./investigations.component.css",
})
export class InvestigationsComponent {
  private readonly api = inject(ApiService);
  protected readonly i18n = inject(I18nService);
  protected readonly statusClass = statusClass;

  protected readonly state = signal<LoadState>("loading");
  protected readonly items = signal<InvestigationSummary[]>([]);

  constructor() {
    this.refresh();
  }

  protected refresh(): void {
    this.state.set("loading");
    this.api.listInvestigations().subscribe({
      next: (items) => {
        this.items.set(items);
        this.state.set("ok");
      },
      error: () => {
        this.items.set([]);
        this.state.set("error");
      },
    });
  }

  /** `created` is epoch seconds on the wire (time.time()). */
  protected formatCreated(epochSeconds: number | null): string {
    if (epochSeconds === null) return "—";
    return new Date(epochSeconds * 1000).toLocaleString(this.i18n.locale());
  }
}
