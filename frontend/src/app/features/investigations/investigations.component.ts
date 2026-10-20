import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { RouterLink } from "@angular/router";

import type { InvestigationSummary } from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { I18nService } from "../../core/i18n/i18n.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { statusClass } from "../../shared/status-class";

type LoadState = "loading" | "ok" | "error";
type SortKey = "created" | "updated" | "status" | "id";
type SortDir = "asc" | "desc";

const PAGE_SIZES = [10, 25, 50] as const;

/**
 * Investigation Studio — history view of the real investigation list
 * (GET /api/v1/investigations, ds-0087 §8.1): client-side search
 * (id/problem), status filter, sortable columns and pagination over
 * the records returned by the API. Real data only; empty/error states
 * are explicit. Entry point to the new-investigation form and to each
 * investigation detail workspace.
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
  private readonly destroyRef = inject(DestroyRef);
  protected readonly i18n = inject(I18nService);
  protected readonly statusClass = statusClass;

  protected readonly state = signal<LoadState>("loading");
  protected readonly items = signal<InvestigationSummary[]>([]);

  /** Client-side view controls (history view §8.1). */
  protected readonly search = signal("");
  protected readonly statusFilter = signal("all");
  protected readonly sortKey = signal<SortKey>("created");
  protected readonly sortDir = signal<SortDir>("desc");
  protected readonly page = signal(0);
  protected readonly pageSize = signal<number>(10);
  protected readonly pageSizes = PAGE_SIZES;

  /** Distinct statuses present in the real payload, alphabetically. */
  protected readonly statuses = computed(() =>
    [...new Set(this.items().map((i) => i.status))].sort(),
  );

  /** Search (id or problem text) + status filter applied to `items`. */
  protected readonly filtered = computed(() => {
    const q = this.search().trim().toLowerCase();
    const status = this.statusFilter();
    return this.items().filter((i) => {
      if (status !== "all" && i.status !== status) return false;
      if (!q) return true;
      return (
        i.investigation_id.toLowerCase().includes(q) ||
        (i.problem ?? "").toLowerCase().includes(q)
      );
    });
  });

  /** `filtered` sorted by the selected key/direction. */
  protected readonly sorted = computed(() => {
    const key = this.sortKey();
    const dir = this.sortDir() === "asc" ? 1 : -1;
    return [...this.filtered()].sort((a, b) => {
      let cmp = 0;
      switch (key) {
        case "created":
          cmp = (a.created ?? 0) - (b.created ?? 0);
          break;
        case "updated":
          cmp = (a.updated ?? 0) - (b.updated ?? 0);
          break;
        case "status":
          cmp = a.status.localeCompare(b.status);
          break;
        case "id":
          cmp = a.investigation_id.localeCompare(b.investigation_id);
          break;
      }
      return cmp * dir;
    });
  });

  protected readonly totalPages = computed(() =>
    Math.max(1, Math.ceil(this.sorted().length / this.pageSize())),
  );

  /** Current page clamped into the valid range after filtering. */
  protected readonly currentPage = computed(() =>
    Math.min(this.page(), this.totalPages() - 1),
  );

  protected readonly paged = computed(() => {
    const start = this.currentPage() * this.pageSize();
    return this.sorted().slice(start, start + this.pageSize());
  });

  constructor() {
    this.refresh();
  }

  protected refresh(): void {
    this.state.set("loading");
    this.api
      .listInvestigations()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (items) => {
          this.items.set(items);
          this.page.set(0);
          this.state.set("ok");
        },
        error: () => {
          this.items.set([]);
          this.state.set("error");
        },
      });
  }

  protected onSearchInput(event: Event): void {
    this.search.set((event.target as HTMLInputElement).value);
    this.page.set(0);
  }

  protected onStatusChange(event: Event): void {
    this.statusFilter.set((event.target as HTMLSelectElement).value);
    this.page.set(0);
  }

  protected onPageSizeChange(event: Event): void {
    const size = Number((event.target as HTMLSelectElement).value);
    this.pageSize.set(PAGE_SIZES.includes(size as 10 | 25 | 50) ? size : 10);
    this.page.set(0);
  }

  /** Toggle direction when re-clicking the active sort column. */
  protected toggleSort(key: SortKey): void {
    if (this.sortKey() === key) {
      this.sortDir.update((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      this.sortKey.set(key);
      this.sortDir.set(key === "created" || key === "updated" ? "desc" : "asc");
    }
  }

  /** aria-sort value for a column header ("none" when not sorted). */
  protected ariaSort(key: SortKey): "ascending" | "descending" | "none" {
    if (this.sortKey() !== key) return "none";
    return this.sortDir() === "asc" ? "ascending" : "descending";
  }

  protected sortMark(key: SortKey): string {
    if (this.sortKey() !== key) return "";
    return this.sortDir() === "asc" ? " ▲" : " ▼";
  }

  protected prevPage(): void {
    this.page.update((p) => Math.max(0, p - 1));
  }

  protected nextPage(): void {
    this.page.update((p) => Math.min(this.totalPages() - 1, p + 1));
  }

  /** `created`/`updated` are epoch seconds on the wire (time.time()). */
  protected formatEpoch(epochSeconds: number | null): string {
    if (epochSeconds === null) return "—";
    return new Date(epochSeconds * 1000).toLocaleString(this.i18n.locale());
  }
}
