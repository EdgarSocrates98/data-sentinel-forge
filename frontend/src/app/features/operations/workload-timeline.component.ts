import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
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
  BaselineKind,
  CompareResponse,
  ExecutionSnapshot,
} from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { I18nService } from "../../core/i18n/i18n.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { apiErrorDetail } from "../../shared/tool-manifest";
import { CompareResultComponent } from "./compare-result.component";
import { OpsNavComponent } from "./ops-nav.component";

type LoadState = "loading" | "ok" | "error";
type CompareState = "idle" | "loading" | "ok" | "error";

/**
 * Workload timeline (ds-0087 §8.3): snapshots of a selected job_id
 * ordered by `started_at` (same ordering the API applies). Selecting
 * a row exposes the compare form — POST /history/compare — and the
 * result renders through the shared compare-result view. Snapshots
 * without job_id cannot form a timeline and are declared as such.
 */
@Component({
  selector: "ds-workload-timeline",
  standalone: true,
  imports: [
    ReactiveFormsModule,
    TranslatePipe,
    OpsNavComponent,
    CompareResultComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./workload-timeline.component.html",
  styleUrl: "./workload-timeline.component.css",
})
export class WorkloadTimelineComponent {
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  protected readonly i18n = inject(I18nService);

  protected readonly state = signal<LoadState>("loading");
  protected readonly snapshots = signal<ExecutionSnapshot[]>([]);

  protected readonly platformFilter = signal("all");
  protected readonly selectedJob = signal("");
  protected readonly selectedSnapshotId = signal<string | null>(null);

  protected readonly compareState = signal<CompareState>("idle");
  protected readonly compareResult = signal<CompareResponse | null>(null);
  protected readonly compareError = signal<string | null>(null);

  protected readonly compareForm = this.fb.nonNullable.group({
    baseline: this.fb.nonNullable.control<BaselineKind>("previous"),
    referenceId: this.fb.nonNullable.control(""),
  });

  /** Distinct platforms present in the ingested snapshots. */
  protected readonly platforms = computed(() =>
    [...new Set(this.snapshots().map((s) => s.platform))].sort(),
  );

  /**
   * Distinct job_ids (non-null) within the current platform filter —
   * these are the workloads that can form a timeline.
   */
  protected readonly jobs = computed(() =>
    [
      ...new Set(
        this.platformSnapshots()
          .map((s) => s.job_id)
          .filter((j): j is string => j !== null && j !== ""),
      ),
    ].sort(),
  );

  /** Snapshots without job_id — reported honestly, never listed. */
  protected readonly orphans = computed(
    () => this.platformSnapshots().filter((s) => !s.job_id).length,
  );

  protected readonly platformSnapshots = computed(() => {
    const p = this.platformFilter();
    return p === "all"
      ? this.snapshots()
      : this.snapshots().filter((s) => s.platform === p);
  });

  /** Timeline rows for the selected job, ordered by started_at. */
  protected readonly timeline = computed(() => {
    const job = this.selectedJob();
    if (!job) return [];
    return this.snapshots()
      .filter((s) => s.job_id === job)
      .sort((a, b) => (a.started_at ?? "").localeCompare(b.started_at ?? ""));
  });

  protected readonly selectedSnapshot = computed(
    () =>
      this.timeline().find(
        (s) => s.snapshot_id === this.selectedSnapshotId(),
      ) ?? null,
  );

  protected readonly needsReference = computed(
    () => this.compareForm.controls.baseline.value === "reference",
  );

  constructor() {
    this.refresh();
    // reference_id is required only for the "reference" baseline.
    this.compareForm.controls.baseline.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((baseline) => {
        const ref = this.compareForm.controls.referenceId;
        if (baseline === "reference") {
          ref.addValidators(Validators.required);
        } else {
          ref.clearValidators();
        }
        ref.updateValueAndValidity();
      });
  }

  protected refresh(): void {
    this.state.set("loading");
    this.api
      .listSnapshots()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (snaps) => {
          this.snapshots.set(snaps);
          this.state.set("ok");
          // Preselect the first job when none is chosen yet.
          if (!this.selectedJob() && this.jobs().length) {
            this.selectedJob.set(this.jobs()[0]!);
          }
        },
        error: () => {
          this.snapshots.set([]);
          this.state.set("error");
        },
      });
  }

  protected onPlatformChange(event: Event): void {
    this.platformFilter.set((event.target as HTMLSelectElement).value);
    this.pageResetSelection();
  }

  protected onJobChange(event: Event): void {
    this.selectedJob.set((event.target as HTMLSelectElement).value);
    this.pageResetSelection();
  }

  protected selectSnapshot(id: string): void {
    this.selectedSnapshotId.set(id);
    this.compareState.set("idle");
    this.compareResult.set(null);
    this.compareError.set(null);
  }

  /** POST /history/compare for the selected snapshot. */
  protected runCompare(): void {
    const snap = this.selectedSnapshot();
    if (!snap || this.compareForm.invalid) {
      this.compareForm.markAllAsTouched();
      return;
    }
    const { baseline, referenceId } = this.compareForm.getRawValue();
    this.compareState.set("loading");
    this.compareResult.set(null);
    this.compareError.set(null);
    this.api
      .compareSnapshots({
        snapshot_id: snap.snapshot_id,
        baseline,
        reference_id:
          baseline === "reference" ? referenceId || null : undefined,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.compareResult.set(res);
          this.compareState.set("ok");
        },
        error: (err: unknown) => {
          this.compareError.set(apiErrorDetail(err));
          this.compareState.set("error");
        },
      });
  }

  private pageResetSelection(): void {
    this.selectedSnapshotId.set(null);
    this.compareState.set("idle");
    this.compareResult.set(null);
    this.compareError.set(null);
    if (!this.jobs().includes(this.selectedJob())) {
      this.selectedJob.set(this.jobs()[0] ?? "");
    }
  }

  /** started_at/ended_at are ISO-8601 strings on the wire. */
  protected formatIso(iso: string | null): string {
    if (!iso) return "—";
    const d = new Date(iso);
    return Number.isNaN(d.getTime())
      ? iso
      : d.toLocaleString(this.i18n.locale());
  }

  protected fmtNum(v: number | null, unit = ""): string {
    if (v === null) return "—";
    return `${v}${unit}`;
  }
}
