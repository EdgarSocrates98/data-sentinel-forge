import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { forkJoin, of } from "rxjs";
import { catchError } from "rxjs/operators";

import type {
  AlertRecord,
  ExecutionSnapshot,
  PlanSummary,
  WatchSummary,
} from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { severityClass } from "../../shared/status-class";
import { OpsNavComponent } from "./ops-nav.component";

type LoadState = "loading" | "ok" | "error";

const SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];

/** Count rows ([label, count]) used by the dashboard stat cards. */
function countEntries(
  values: string[],
  order?: readonly string[],
): Array<[string, number]> {
  const m = new Map<string, number>();
  for (const v of values) m.set(v, (m.get(v) ?? 0) + 1);
  const rows = [...m.entries()];
  if (order) {
    rows.sort(
      (a, b) =>
        (order.indexOf(a[0]) === -1 ? order.length : order.indexOf(a[0])) -
        (order.indexOf(b[0]) === -1 ? order.length : order.indexOf(b[0])),
    );
  } else {
    rows.sort(([a], [b]) => a.localeCompare(b));
  }
  return rows;
}

/**
 * Operational dashboard (ds-0087 §8.2): real counters only —
 * snapshots by platform, alerts by severity, watches enabled/disabled
 * and remediation plans by state. Each endpoint is queried
 * independently so a missing endpoint degrades to an honest
 * "unavailable" card instead of hiding the others. No fabricated
 * metrics.
 */
@Component({
  selector: "ds-operations-dashboard",
  standalone: true,
  imports: [TranslatePipe, OpsNavComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./operations-dashboard.component.html",
  styleUrl: "./operations-dashboard.component.css",
})
export class OperationsDashboardComponent {
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly severityClass = severityClass;

  protected readonly state = signal<LoadState>("loading");
  /** null = endpoint unavailable/failed; [] = loaded and empty. */
  protected readonly snapshots = signal<ExecutionSnapshot[] | null>(null);
  protected readonly alerts = signal<AlertRecord[] | null>(null);
  protected readonly watches = signal<WatchSummary[] | null>(null);
  protected readonly plans = signal<PlanSummary[] | null>(null);

  protected readonly snapshotsByPlatform = computed(() =>
    countEntries((this.snapshots() ?? []).map((s) => s.platform)),
  );

  protected readonly alertsBySeverity = computed(() =>
    countEntries(
      (this.alerts() ?? []).map((a) => a.severity),
      SEVERITY_ORDER,
    ),
  );

  protected readonly alertsRecovered = computed(
    () => (this.alerts() ?? []).filter((a) => a.recovered).length,
  );

  protected readonly watchesEnabled = computed(
    () => (this.watches() ?? []).filter((w) => w.enabled).length,
  );

  protected readonly watchesDisabled = computed(
    () => (this.watches() ?? []).filter((w) => !w.enabled).length,
  );

  protected readonly plansByState = computed(() =>
    countEntries((this.plans() ?? []).map((p) => p.state)),
  );

  constructor() {
    this.refresh();
  }

  protected refresh(): void {
    this.state.set("loading");
    forkJoin({
      snapshots: this.api
        .listSnapshots()
        .pipe(catchError(() => of(null))),
      alerts: this.api.listAlerts().pipe(catchError(() => of(null))),
      watches: this.api.listWatches().pipe(catchError(() => of(null))),
      plans: this.api.listPlans().pipe(catchError(() => of(null))),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.snapshots.set(res.snapshots);
          this.alerts.set(res.alerts);
          this.watches.set(res.watches);
          this.plans.set(res.plans);
          // Every endpoint failed → honest top-level error; partial
          // failures render per-card "unavailable" notes instead.
          this.state.set(
            res.snapshots === null &&
              res.alerts === null &&
              res.watches === null &&
              res.plans === null
              ? "error"
              : "ok",
          );
        },
        error: () => this.state.set("error"),
      });
  }
}
