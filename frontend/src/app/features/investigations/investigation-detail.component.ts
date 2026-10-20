import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  computed,
  inject,
  signal,
} from "@angular/core";
import { ActivatedRoute, RouterLink } from "@angular/router";
import { Subscription } from "rxjs";

import {
  InvestigationReport,
  InvestigationStreamEvent,
  isInvestigationReport,
} from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { I18nService } from "../../core/i18n/i18n.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import {
  confidenceClass,
  severityClass,
  statusClass,
} from "../../shared/status-class";
import { InvestigationStreamService } from "./investigation-stream.service";

type PageState =
  | "loading"
  | "running"
  | "report"
  | "failed"
  | "notfound"
  | "error";

interface ToolCallEntry {
  toolId: string;
  ok: boolean;
  durationMs: number | null;
}

interface ValidationSummary {
  checked: number;
  errors: string[];
  warnings: string[];
}

/**
 * Investigation workspace (ds-0073 §5.3-5.5): summary, agent/tool
 * activity, findings, hypotheses, evidence inspector, conclusions,
 * recommendations and limitations — all from the real
 * InvestigationReport payload. While the investigation runs, progress
 * comes from the SSE stream (GET …/stream); no data is simulated.
 */
@Component({
  selector: "ds-investigation-detail",
  standalone: true,
  imports: [RouterLink, TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./investigation-detail.component.html",
  styleUrl: "./investigation-detail.component.css",
})
export class InvestigationDetailComponent implements OnDestroy {
  private readonly api = inject(ApiService);
  private readonly stream = inject(InvestigationStreamService);
  private readonly route = inject(ActivatedRoute);
  protected readonly i18n = inject(I18nService);

  protected readonly severityClass = severityClass;
  protected readonly confidenceClass = confidenceClass;
  protected readonly statusClass = statusClass;

  protected readonly state = signal<PageState>("loading");
  protected readonly investigationId = signal("");
  protected readonly report = signal<InvestigationReport | null>(null);
  protected readonly events = signal<InvestigationStreamEvent[]>([]);
  protected readonly streamError = signal(false);
  protected readonly failureMessage = signal<string | null>(null);
  protected readonly expandedFindings = signal<ReadonlySet<string>>(
    new Set(),
  );

  /** Real per-tool executions recorded in `report.context.tool_calls`. */
  protected readonly toolCalls = computed<ToolCallEntry[]>(() => {
    const raw = this.report()?.context["tool_calls"];
    if (!Array.isArray(raw)) return [];
    return raw
      .filter(
        (e): e is Record<string, unknown> =>
          !!e && typeof e === "object" && "tool_id" in e,
      )
      .map((e) => ({
        toolId: String(e["tool_id"]),
        ok: e["ok"] === true,
        durationMs: typeof e["duration_ms"] === "number" ? e["duration_ms"] : null,
      }));
  });

  /** Independent-validator summary stored in `report.context.validation`. */
  protected readonly validation = computed<ValidationSummary | null>(() => {
    const raw = this.report()?.context["validation"];
    if (!raw || typeof raw !== "object") return null;
    const v = raw as Record<string, unknown>;
    return {
      checked: typeof v["checked"] === "number" ? v["checked"] : 0,
      errors: Array.isArray(v["errors"]) ? (v["errors"] as string[]) : [],
      warnings: Array.isArray(v["warnings"])
        ? (v["warnings"] as string[])
        : [],
    };
  });

  private streamSub: Subscription | null = null;
  private readonly routeSub: Subscription;

  constructor() {
    this.routeSub = this.route.paramMap.subscribe((params) => {
      const id = params.get("id") ?? "";
      this.investigationId.set(id);
      this.load();
    });
  }

  ngOnDestroy(): void {
    this.routeSub.unsubscribe();
    this.closeStream();
  }

  protected load(): void {
    const id = this.investigationId();
    if (!id) {
      this.state.set("notfound");
      return;
    }
    this.closeStream();
    this.state.set("loading");
    this.streamError.set(false);
    this.failureMessage.set(null);
    // Reset per-investigation view state — switching ids must not
    // leak a previous investigation's events or findings (review).
    this.events.set([]);
    this.expandedFindings.set(new Set());
    this.api.getInvestigation(id).subscribe({
      next: (detail) => {
        if (isInvestigationReport(detail)) {
          this.report.set(detail);
          this.state.set("report");
        } else {
          this.state.set("running");
          this.openStream();
        }
      },
      error: (err: { status?: number }) => {
        this.state.set(err.status === 404 ? "notfound" : "error");
      },
    });
  }

  /** Subscribe to the live SSE stream for the running investigation. */
  private openStream(): void {
    this.closeStream();
    const url = this.api.investigationStreamUrl(this.investigationId());
    this.streamSub = this.stream.open(url).subscribe({
      next: (event) => {
        this.events.update((all) => [...all, event]);
        if (event.event === "INVESTIGATION_COMPLETED") {
          this.refreshReport();
        } else if (event.event === "INVESTIGATION_FAILED") {
          const msg = event.data["error"];
          this.failureMessage.set(
            typeof msg === "string" ? msg : null,
          );
          this.state.set("failed");
        }
      },
      error: () => this.streamError.set(true),
      // The server closes the stream after the terminal event; if it
      // ends without one (edge cases), reconcile state instead of
      // leaving the page stuck in "running" (review).
      complete: () => {
        if (this.state() === "running") {
          this.refreshReport();
        }
      },
    });
  }

  /** After a terminal stream event, fetch the finished report. */
  private refreshReport(): void {
    this.api.getInvestigation(this.investigationId()).subscribe({
      next: (detail) => {
        if (isInvestigationReport(detail)) {
          this.report.set(detail);
          this.state.set("report");
        }
        // A "completed" event without a finished report keeps the
        // running view; the manual retry button remains available.
      },
      error: () => this.streamError.set(true),
    });
  }

  private closeStream(): void {
    this.streamSub?.unsubscribe();
    this.streamSub = null;
  }

  /** Export the real report payload as JSON (no fabricated data). */
  protected exportReport(): void {
    const rep = this.report();
    if (!rep) return;
    const blob = new Blob([JSON.stringify(rep, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${rep.investigation_id}.report.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  /** Human-readable label for a stream event name. */
  protected eventLabel(event: InvestigationStreamEvent): string {
    const tool = event.data["tool"];
    if (event.event === "TOOL_COMPLETED" && typeof tool === "string") {
      return `${event.event} — ${tool}`;
    }
    return event.event;
  }

  protected toggleFinding(id: string): void {
    this.expandedFindings.update((set) => {
      const next = new Set(set);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  /** Pretty-print small context dicts (provenance, access metadata). */
  protected kvEntries(obj: Record<string, unknown>): Array<[string, string]> {
    return Object.entries(obj).map(([k, v]) => [
      k,
      typeof v === "object" ? JSON.stringify(v) : String(v),
    ]);
  }
}
