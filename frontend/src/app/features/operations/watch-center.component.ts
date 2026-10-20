import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from "@angular/forms";

import type {
  AlertRecord,
  Severity,
  WatchRunAlert,
  WatchSummary,
} from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { I18nService } from "../../core/i18n/i18n.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { severityClass } from "../../shared/status-class";
import { apiErrorDetail } from "../../shared/tool-manifest";
import { OpsNavComponent } from "./ops-nav.component";

type LoadState = "loading" | "ok" | "error";

/** Minimum interval enforced server-side (watch/engine.py). */
const MIN_INTERVAL_S = 30;

/** Watch rules understood by the engine (WatchDefinition.rule). */
const WATCH_RULES = ["regression", "failure", "threshold"] as const;
const SEVERITIES: readonly Severity[] = [
  "INFO",
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
];

/** Platform suggestions (snapshot contract comment) — free text. */
const PLATFORM_HINTS = [
  "glue",
  "emr-ec2",
  "emr-serverless",
  "emr-eks",
  "spark",
  "openlineage",
];

/** Signal names evaluated by history.regression (SIGNALS). */
const METRIC_HINTS = [
  "duration_s",
  "failure_rate",
  "retry_count",
  "cpu_utilization",
  "memory_utilization",
  "shuffle_spill_bytes",
  "throughput",
  "input_bytes",
  "output_bytes",
  "data_freshness_s",
  "quality_score",
  "iceberg_file_count",
  "estimated_cost",
];

interface RunOutcome {
  state: "loading" | "ok" | "error";
  alerts: WatchRunAlert[];
  detail: string | null;
}

/**
 * Watch center (ds-0087 §8.5): CRUD + manual evaluation of local
 * watches over ingested snapshots. Watches are created DISABLED by
 * the API and nothing here starts automatic monitoring — evaluation
 * only happens through the explicit POST /watches/{id}/run action.
 */
@Component({
  selector: "ds-watch-center",
  standalone: true,
  imports: [ReactiveFormsModule, TranslatePipe, OpsNavComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./watch-center.component.html",
  styleUrl: "./watch-center.component.css",
})
export class WatchCenterComponent {
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  protected readonly i18n = inject(I18nService);
  protected readonly severityClass = severityClass;

  protected readonly watchesState = signal<LoadState>("loading");
  protected readonly watches = signal<WatchSummary[]>([]);
  protected readonly alertsState = signal<LoadState>("loading");
  protected readonly alerts = signal<AlertRecord[]>([]);

  protected readonly creating = signal(false);
  protected readonly createError = signal<string | null>(null);
  protected readonly createdId = signal<string | null>(null);

  /** watch_id currently busy with a pause/resume/delete/run action. */
  protected readonly busyId = signal<string | null>(null);
  /** watch_id awaiting delete confirmation (two-step delete). */
  protected readonly pendingDelete = signal<string | null>(null);
  protected readonly actionError = signal<string | null>(null);

  /** Last manual evaluation per watch (session display only). */
  protected readonly runResults = signal<Map<string, RunOutcome>>(
    new Map(),
  );

  protected readonly rules = WATCH_RULES;
  protected readonly severities = SEVERITIES;
  protected readonly platformHints = PLATFORM_HINTS;
  protected readonly metricHints = METRIC_HINTS;
  protected readonly minInterval = MIN_INTERVAL_S;

  protected readonly form = this.fb.nonNullable.group({
    watch_id: this.fb.nonNullable.control("", Validators.required),
    workload: this.fb.nonNullable.control("", Validators.required),
    platform: this.fb.nonNullable.control("", Validators.required),
    metrics: this.fb.nonNullable.control(""),
    rule: this.fb.nonNullable.control<string>("regression"),
    interval_s: this.fb.nonNullable.control(300, [
      Validators.required,
      Validators.min(MIN_INTERVAL_S),
    ]),
    severity: this.fb.nonNullable.control<Severity>("MEDIUM"),
  });

  constructor() {
    this.refreshWatches();
    this.refreshAlerts();
  }

  protected refreshWatches(): void {
    this.watchesState.set("loading");
    this.api
      .listWatches()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (watches) => {
          this.watches.set(watches);
          this.watchesState.set("ok");
        },
        error: () => {
          this.watches.set([]);
          this.watchesState.set("error");
        },
      });
  }

  protected refreshAlerts(): void {
    this.alertsState.set("loading");
    this.api
      .listAlerts()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (alerts) => {
          this.alerts.set(alerts);
          this.alertsState.set("ok");
        },
        error: () => {
          this.alerts.set([]);
          this.alertsState.set("error");
        },
      });
  }

  /** POST /watches — creates a DISABLED watch by design. */
  protected createWatch(): void {
    if (this.form.invalid || this.creating()) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    const metrics = v.metrics
      .split(",")
      .map((m) => m.trim())
      .filter((m) => m.length > 0);
    this.creating.set(true);
    this.createError.set(null);
    this.createdId.set(null);
    this.api
      .createWatch({
        watch_id: v.watch_id.trim(),
        workload: v.workload.trim(),
        platform: v.platform.trim(),
        source: "local",
        metrics,
        rule: v.rule,
        interval_s: v.interval_s,
        severity: v.severity,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.creating.set(false);
          this.createdId.set(res.watch_id);
          this.form.reset({
            watch_id: "",
            workload: "",
            platform: "",
            metrics: "",
            rule: "regression",
            interval_s: 300,
            severity: "MEDIUM",
          });
          this.refreshWatches();
        },
        error: (err: unknown) => {
          this.creating.set(false);
          this.createError.set(apiErrorDetail(err));
        },
      });
  }

  /** POST /watches/{id}/run — single manual evaluation. */
  protected runWatch(id: string): void {
    if (this.busyId()) return;
    this.busyId.set(id);
    this.actionError.set(null);
    this.runResults.update((m) => {
      const n = new Map(m);
      n.set(id, { state: "loading", alerts: [], detail: null });
      return n;
    });
    this.api
      .runWatch(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (alerts) => {
          this.busyId.set(null);
          this.runResults.update((m) => {
            const n = new Map(m);
            n.set(id, { state: "ok", alerts, detail: null });
            return n;
          });
          // Emitted alerts land in engine history — refresh the list.
          if (alerts.length) this.refreshAlerts();
        },
        error: (err: unknown) => {
          this.busyId.set(null);
          this.runResults.update((m) => {
            const n = new Map(m);
            n.set(id, {
              state: "error",
              alerts: [],
              detail: apiErrorDetail(err),
            });
            return n;
          });
        },
      });
  }

  protected pauseWatch(id: string): void {
    this.mutateWatch(id, () => this.api.pauseWatch(id));
  }

  protected resumeWatch(id: string): void {
    this.mutateWatch(id, () => this.api.resumeWatch(id));
  }

  /** First step of the two-step delete (no destructive one-click). */
  protected requestDelete(id: string): void {
    this.pendingDelete.set(id);
  }

  protected cancelDelete(): void {
    this.pendingDelete.set(null);
  }

  protected confirmDelete(id: string): void {
    this.pendingDelete.set(null);
    this.actionError.set(null);
    this.busyId.set(id);
    this.api
      .deleteWatch(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.busyId.set(null);
          this.runResults.update((m) => {
            const n = new Map(m);
            n.delete(id);
            return n;
          });
          this.refreshWatches();
        },
        error: (err: unknown) => {
          this.busyId.set(null);
          this.actionError.set(apiErrorDetail(err));
        },
      });
  }

  private mutateWatch(
    id: string,
    call: () => ReturnType<ApiService["pauseWatch"]>,
  ): void {
    if (this.busyId()) return;
    this.busyId.set(id);
    this.actionError.set(null);
    call()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.busyId.set(null);
          this.refreshWatches();
        },
        error: (err: unknown) => {
          this.busyId.set(null);
          this.actionError.set(apiErrorDetail(err));
        },
      });
  }

  protected runOutcome(id: string): RunOutcome | null {
    return this.runResults().get(id) ?? null;
  }

  /** `ts` is epoch seconds on the wire. */
  protected formatTs(epochSeconds: number): string {
    return new Date(epochSeconds * 1000).toLocaleString(this.i18n.locale());
  }
}
