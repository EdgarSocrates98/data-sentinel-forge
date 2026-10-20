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
  RegressionFinding,
} from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { apiErrorDetail } from "../../shared/tool-manifest";
import { CompareResultComponent } from "./compare-result.component";
import { OpsNavComponent } from "./ops-nav.component";
import { RegressionFindingsComponent } from "./regression-findings.component";

type LoadState = "loading" | "ok" | "error";
type AsyncState = "idle" | "loading" | "ok" | "error";

/**
 * Regression explorer (ds-0087 §8.4): pick an ingested snapshot, run
 * POST /history/compare against a real baseline (previous | median |
 * reference run), and inspect deltas, drift, findings, confidence and
 * limitations. A second section calls GET /history/regressions so the
 * snapshot is also evaluated against the full job history — a
 * different semantic from the chosen baseline.
 */
@Component({
  selector: "ds-regression-explorer",
  standalone: true,
  imports: [
    ReactiveFormsModule,
    TranslatePipe,
    OpsNavComponent,
    CompareResultComponent,
    RegressionFindingsComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./regression-explorer.component.html",
  styleUrl: "./regression-explorer.component.css",
})
export class RegressionExplorerComponent {
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);

  protected readonly state = signal<LoadState>("loading");
  protected readonly snapshots = signal<ExecutionSnapshot[]>([]);
  protected readonly platformFilter = signal("all");
  protected readonly selectedId = signal("");

  protected readonly compareState = signal<AsyncState>("idle");
  protected readonly compareResult = signal<CompareResponse | null>(null);
  protected readonly compareError = signal<string | null>(null);

  /** GET /history/regressions result — independent of the baseline. */
  protected readonly historyState = signal<AsyncState>("idle");
  protected readonly historyFindings = signal<RegressionFinding[]>([]);
  protected readonly historyError = signal<string | null>(null);

  protected readonly compareForm = this.fb.nonNullable.group({
    snapshot: this.fb.nonNullable.control("", Validators.required),
    baseline: this.fb.nonNullable.control<BaselineKind>("previous"),
    referenceId: this.fb.nonNullable.control(""),
  });

  protected readonly platforms = computed(() =>
    [...new Set(this.snapshots().map((s) => s.platform))].sort(),
  );

  /** Snapshot options honoring the platform filter. */
  protected readonly options = computed(() => {
    const p = this.platformFilter();
    const list =
      p === "all"
        ? this.snapshots()
        : this.snapshots().filter((s) => s.platform === p);
    return [...list].sort((a, b) =>
      (b.started_at ?? "").localeCompare(a.started_at ?? ""),
    );
  });

  protected readonly selected = computed(
    () =>
      this.snapshots().find((s) => s.snapshot_id === this.selectedId()) ??
      null,
  );

  protected readonly needsReference = computed(
    () => this.compareForm.controls.baseline.value === "reference",
  );

  constructor() {
    this.refresh();
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
    this.compareForm.controls.snapshot.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((id) => this.onSnapshotSelected(id));
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
        },
        error: () => {
          this.snapshots.set([]);
          this.state.set("error");
        },
      });
  }

  protected onPlatformChange(event: Event): void {
    this.platformFilter.set((event.target as HTMLSelectElement).value);
    const opts = this.options();
    if (!opts.some((s) => s.snapshot_id === this.selectedId())) {
      this.compareForm.controls.snapshot.setValue("");
    }
  }

  /** Snapshot selection: reset compare, load history regressions. */
  private onSnapshotSelected(id: string): void {
    this.selectedId.set(id);
    this.compareState.set("idle");
    this.compareResult.set(null);
    this.compareError.set(null);
    this.loadHistoryRegressions();
  }

  protected retryHistory(): void {
    this.loadHistoryRegressions();
  }

  /**
   * GET /history/regressions — requires job_id; snapshots without one
   * get an honest unavailable note instead of a request.
   */
  private loadHistoryRegressions(): void {
    const snap = this.selected();
    this.historyFindings.set([]);
    this.historyError.set(null);
    if (!snap || !snap.job_id) {
      this.historyState.set("idle");
      return;
    }
    this.historyState.set("loading");
    this.api
      .listRegressions(snap.job_id, snap.snapshot_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (findings) => {
          this.historyFindings.set(findings);
          this.historyState.set("ok");
        },
        error: (err: unknown) => {
          this.historyError.set(apiErrorDetail(err));
          this.historyState.set("error");
        },
      });
  }

  protected runCompare(): void {
    if (this.compareForm.invalid) {
      this.compareForm.markAllAsTouched();
      return;
    }
    const { snapshot, baseline, referenceId } =
      this.compareForm.getRawValue();
    this.compareState.set("loading");
    this.compareResult.set(null);
    this.compareError.set(null);
    this.api
      .compareSnapshots({
        snapshot_id: snapshot,
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

  /** Option label: snapshot_id + platform/job context. */
  protected optionLabel(s: ExecutionSnapshot): string {
    const job = s.job_id ?? "—";
    return `${s.snapshot_id} — ${s.platform} · ${job}`;
  }
}
