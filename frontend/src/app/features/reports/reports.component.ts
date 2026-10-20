import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from "@angular/core";
import { RouterLink } from "@angular/router";
import { forkJoin } from "rxjs";

import type {
  InvestigationReport,
  InvestigationSummary,
} from "../../core/api.models";
import { isInvestigationReport } from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { I18nService } from "../../core/i18n/i18n.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";

type LoadState = "loading" | "ok" | "error";
type CompareState = "idle" | "loading" | "ok" | "error";

/** One metric row in the side-by-side report comparison. */
interface DiffRow {
  labelKey: string;
  suffix: string;
  a: string;
  b: string;
  differs: boolean;
}

function countByAttr(
  report: InvestigationReport,
  attr: "severity" | "status",
): Map<string, number> {
  const m = new Map<string, number>();
  for (const f of report.findings) {
    const k = String(f[attr]).toUpperCase();
    m.set(k, (m.get(k) ?? 0) + 1);
  }
  return m;
}

/**
 * Reporting & History (ds-0077, spec 06.9): the real investigation
 * list — which is the session history (the API keeps investigations
 * in-memory per process, declared honestly) — with client-side
 * filter/sort, per-report JSON export of the real payload, and a
 * two-report side-by-side comparison derived only from fetched
 * reports.
 */
@Component({
  selector: "ds-reports",
  standalone: true,
  imports: [RouterLink, TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./reports.component.html",
  styleUrl: "./reports.component.css",
})
export class ReportsComponent {
  private readonly api = inject(ApiService);
  protected readonly i18n = inject(I18nService);

  protected readonly listState = signal<LoadState>("loading");
  protected readonly items = signal<InvestigationSummary[]>([]);
  protected readonly filter = signal("");
  protected readonly exporting = signal<ReadonlySet<string>>(new Set());
  protected readonly exportError = signal<string | null>(null);

  protected readonly cmpA = signal("");
  protected readonly cmpB = signal("");
  protected readonly cmpState = signal<CompareState>("idle");
  protected readonly reportA = signal<InvestigationReport | null>(null);
  protected readonly reportB = signal<InvestigationReport | null>(null);

  /** Filtered + sorted (newest first) session list. */
  protected readonly filtered = computed(() => {
    const q = this.filter().trim().toLowerCase();
    const list = q
      ? this.items().filter((i) =>
          i.investigation_id.toLowerCase().includes(q),
        )
      : this.items();
    return [...list].sort((a, b) => (b.created ?? 0) - (a.created ?? 0));
  });

  /** Side-by-side metric rows (only real report fields). */
  protected readonly diffRows = computed<DiffRow[]>(() => {
    const a = this.reportA();
    const b = this.reportB();
    if (!a || !b) return [];
    const rows: DiffRow[] = [];
    const push = (labelKey: string, suffix: string, va: string, vb: string) =>
      rows.push({ labelKey, suffix, a: va, b: vb, differs: va !== vb });

    push("reports.cmp.problem", "", a.problem || "—", b.problem || "—");
    push(
      "reports.cmp.findingsTotal",
      "",
      String(a.findings.length),
      String(b.findings.length),
    );
    const sevA = countByAttr(a, "severity");
    const sevB = countByAttr(b, "severity");
    for (const k of [...new Set([...sevA.keys(), ...sevB.keys()])].sort()) {
      push(
        "reports.cmp.severityPrefix",
        k,
        String(sevA.get(k) ?? 0),
        String(sevB.get(k) ?? 0),
      );
    }
    const stA = countByAttr(a, "status");
    const stB = countByAttr(b, "status");
    for (const k of [...new Set([...stA.keys(), ...stB.keys()])].sort()) {
      push(
        "reports.cmp.statusPrefix",
        k,
        String(stA.get(k) ?? 0),
        String(stB.get(k) ?? 0),
      );
    }
    push(
      "reports.cmp.tokens",
      "",
      String(a.tokens_used),
      String(b.tokens_used),
    );
    push("reports.cmp.cost", "", String(a.cost_usd), String(b.cost_usd));
    push(
      "reports.cmp.duration",
      "",
      `${a.duration_seconds}s`,
      `${b.duration_seconds}s`,
    );
    push(
      "reports.cmp.conclusions",
      "",
      String(a.conclusions.length),
      String(b.conclusions.length),
    );
    push(
      "reports.cmp.limitations",
      "",
      String(a.limitations.length),
      String(b.limitations.length),
    );
    return rows;
  });

  /** Tools unique to each report + common tools — real sets. */
  protected readonly toolDiff = computed(() => {
    const a = this.reportA();
    const b = this.reportB();
    if (!a || !b) return null;
    const setA = new Set(a.tools_used);
    const setB = new Set(b.tools_used);
    return {
      onlyA: [...setA].filter((t) => !setB.has(t)).sort(),
      onlyB: [...setB].filter((t) => !setA.has(t)).sort(),
      both: [...setA].filter((t) => setB.has(t)).sort(),
    };
  });

  constructor() {
    this.refresh();
  }

  protected refresh(): void {
    this.listState.set("loading");
    this.api.listInvestigations().subscribe({
      next: (items) => {
        this.items.set(items);
        this.listState.set("ok");
      },
      error: () => {
        this.items.set([]);
        this.listState.set("error");
      },
    });
  }

  protected formatCreated(epochSeconds: number | null): string {
    if (epochSeconds === null) return "—";
    return new Date(epochSeconds * 1000).toLocaleString(this.i18n.locale());
  }

  protected onFilterInput(event: Event): void {
    this.filter.set((event.target as HTMLInputElement).value);
  }

  /** Fetch the real report then download it as a JSON blob. */
  protected exportReport(id: string): void {
    if (this.exporting().has(id)) return;
    this.exporting.update((s) => new Set(s).add(id));
    this.exportError.set(null);
    this.api.getInvestigation(id).subscribe({
      next: (detail) => {
        this.exporting.update((s) => {
          const n = new Set(s);
          n.delete(id);
          return n;
        });
        if (!isInvestigationReport(detail)) {
          this.exportError.set(id);
          return;
        }
        const blob = new Blob([JSON.stringify(detail, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${id}.report.json`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: () => {
        this.exporting.update((s) => {
          const n = new Set(s);
          n.delete(id);
          return n;
        });
        this.exportError.set(id);
      },
    });
  }

  protected selectCompare(side: "a" | "b", id: string): void {
    if (side === "a") {
      this.cmpA.set(id);
    } else {
      this.cmpB.set(id);
    }
    this.loadComparison();
  }

  /** Fetch both reports once two distinct ids are selected. */
  private loadComparison(): void {
    const a = this.cmpA();
    const b = this.cmpB();
    this.reportA.set(null);
    this.reportB.set(null);
    if (!a || !b || a === b) {
      this.cmpState.set("idle");
      return;
    }
    this.cmpState.set("loading");
    forkJoin({
      a: this.api.getInvestigation(a),
      b: this.api.getInvestigation(b),
    }).subscribe({
      next: ({ a: da, b: db }) => {
        this.reportA.set(isInvestigationReport(da) ? da : null);
        this.reportB.set(isInvestigationReport(db) ? db : null);
        this.cmpState.set(
          isInvestigationReport(da) && isInvestigationReport(db)
            ? "ok"
            : "error",
        );
      },
      error: () => this.cmpState.set("error"),
    });
  }
}
