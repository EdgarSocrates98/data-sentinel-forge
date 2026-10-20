import { SlicePipe } from "@angular/common";
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
import { Observable } from "rxjs";

import {
  isInvestigationReport,
  type Finding,
  type InvestigationSummary,
  type PlanDryRunResult,
  type PlanExecutionResult,
  type PlanSummary,
  type ProposedChange,
  type RemediationPlan,
  type Severity,
} from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { I18nService } from "../../core/i18n/i18n.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { apiErrorDetail } from "../../shared/tool-manifest";
import { OpsNavComponent } from "./ops-nav.component";

type LoadState = "loading" | "ok" | "error";
type AsyncState = "idle" | "loading" | "ok" | "error";
type CreateMode = "investigation" | "manual";

/** FindingCategory wire values (core/contracts/enums.py). */
const FINDING_CATEGORIES = [
  "out_of_memory",
  "disk_space",
  "data_skew",
  "configuration",
  "permissions",
  "network_io",
  "dependency",
  "timeout",
  "executor_loss",
  "sql_antipattern",
  "data_quality",
  "cost",
  "security",
  "compatibility",
  "unknown",
] as const;

/** FindingStatus wire values. */
const FINDING_STATUSES = [
  "CONFIRMED",
  "PROBABLE",
  "POSSIBLE",
  "UNKNOWN",
] as const;

const SEVERITIES: readonly Severity[] = [
  "INFO",
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
];

/**
 * Remediation workspace (ds-0087 §8.6): list/create/inspect
 * remediation plans and drive the supervised lifecycle —
 * submit → human approval (named approver) → dry-run → allowlisted
 * local execution. There is no cloud-execution action by design;
 * approval never applies anything.
 */
@Component({
  selector: "ds-remediation-workspace",
  standalone: true,
  imports: [ReactiveFormsModule, TranslatePipe, OpsNavComponent, SlicePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./remediation-workspace.component.html",
  styleUrl: "./remediation-workspace.component.css",
})
export class RemediationWorkspaceComponent {
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  protected readonly i18n = inject(I18nService);

  /* ---- plan list ---- */
  protected readonly listState = signal<LoadState>("loading");
  protected readonly plans = signal<PlanSummary[]>([]);

  /* ---- plan detail ---- */
  protected readonly detailState = signal<AsyncState>("idle");
  protected readonly plan = signal<RemediationPlan | null>(null);
  protected readonly detailError = signal<string | null>(null);

  /* ---- creation ---- */
  protected readonly createMode = signal<CreateMode>("investigation");
  protected readonly invState = signal<LoadState>("loading");
  protected readonly investigations = signal<InvestigationSummary[]>([]);
  protected readonly findingsState = signal<AsyncState>("idle");
  protected readonly findings = signal<Finding[]>([]);
  protected readonly creating = signal(false);
  protected readonly createError = signal<string | null>(null);
  protected readonly createdPlanId = signal<string | null>(null);

  /* ---- lifecycle actions ---- */
  protected readonly acting = signal<string | null>(null);
  protected readonly actionError = signal<string | null>(null);
  protected readonly actionNote = signal<string | null>(null);
  protected readonly dryRun = signal<PlanDryRunResult | null>(null);
  protected readonly execResult = signal<PlanExecutionResult | null>(null);

  protected readonly categories = FINDING_CATEGORIES;
  protected readonly findingStatuses = FINDING_STATUSES;
  protected readonly severities = SEVERITIES;

  /** Create-from-investigation form. */
  protected readonly invForm = this.fb.nonNullable.group({
    investigation: this.fb.nonNullable.control("", Validators.required),
    // disabled until an investigation with findings is picked —
    // driven via the control (not [disabled]) for reactive forms.
    finding: this.fb.nonNullable.control(
      { value: "", disabled: true },
      Validators.required,
    ),
    title: this.fb.nonNullable.control(""),
  });

  /** Manual-finding form (embedded Finding payload). */
  protected readonly manualForm = this.fb.nonNullable.group({
    explanation: this.fb.nonNullable.control("", Validators.required),
    category: this.fb.nonNullable.control<string>("configuration"),
    severity: this.fb.nonNullable.control<Severity>("MEDIUM"),
    status: this.fb.nonNullable.control<string>("POSSIBLE"),
    recommendations: this.fb.nonNullable.control(""),
    title: this.fb.nonNullable.control(""),
  });

  /** Approver name / reject reason for the lifecycle actions. */
  protected readonly actionForm = this.fb.nonNullable.group({
    approver: this.fb.nonNullable.control(""),
    reason: this.fb.nonNullable.control(""),
  });

  /** Only completed investigations carry findings to remediate. */
  protected readonly completedInvestigations = computed(() =>
    this.investigations().filter((i) => i.status === "completed"),
  );

  protected readonly selectedPlanId = computed(
    () => this.plan()?.plan_id ?? null,
  );

  /* ---- state gating (mirrors remediation/plans.py _ALLOWED) ---- */
  protected readonly canSubmit = computed(() =>
    ["DRAFT", "VALIDATED"].includes(this.plan()?.state ?? ""),
  );
  protected readonly canApprove = computed(
    () => this.plan()?.state === "AWAITING_APPROVAL",
  );
  protected readonly canReject = computed(() =>
    ["DRAFT", "VALIDATED", "AWAITING_APPROVAL"].includes(
      this.plan()?.state ?? "",
    ),
  );
  protected readonly canExecuteLocal = computed(
    () => this.plan()?.state === "APPROVED",
  );

  constructor() {
    this.refreshPlans();
    this.loadInvestigations();
    this.invForm.controls.investigation.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((id) => this.loadFindings(id));
  }

  /* ---------------- list ---------------- */

  protected refreshPlans(): void {
    this.listState.set("loading");
    this.api
      .listPlans()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (plans) => {
          this.plans.set(plans);
          this.listState.set("ok");
        },
        error: () => {
          this.plans.set([]);
          this.listState.set("error");
        },
      });
  }

  /* ---------------- detail ---------------- */

  protected openPlan(id: string): void {
    this.detailState.set("loading");
    this.detailError.set(null);
    this.plan.set(null);
    this.dryRun.set(null);
    this.execResult.set(null);
    this.actionError.set(null);
    this.actionNote.set(null);
    this.api
      .getPlan(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (plan) => {
          this.plan.set(plan);
          this.detailState.set("ok");
        },
        error: (err: unknown) => {
          this.detailError.set(apiErrorDetail(err));
          this.detailState.set("error");
        },
      });
  }

  /* ---------------- create ---------------- */

  private loadInvestigations(): void {
    this.invState.set("loading");
    this.api
      .listInvestigations()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (items) => {
          this.investigations.set(items);
          this.invState.set("ok");
        },
        error: () => {
          this.investigations.set([]);
          this.invState.set("error");
        },
      });
  }

  /** Load the report to pick a real finding_id from it. */
  private loadFindings(investigationId: string): void {
    const findingCtl = this.invForm.controls.finding;
    this.findings.set([]);
    findingCtl.setValue("");
    if (!investigationId) {
      findingCtl.disable();
      this.findingsState.set("idle");
      return;
    }
    this.findingsState.set("loading");
    this.api
      .getInvestigation(investigationId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (detail) => {
          const rows = isInvestigationReport(detail)
            ? detail.findings
            : [];
          this.findings.set(rows);
          if (rows.length) {
            findingCtl.enable();
          } else {
            findingCtl.disable();
          }
          this.findingsState.set("ok");
        },
        error: () => {
          findingCtl.disable();
          this.findingsState.set("error");
        },
      });
  }

  protected setCreateMode(mode: CreateMode): void {
    this.createMode.set(mode);
    this.createError.set(null);
  }

  protected createPlan(): void {
    if (this.creating()) return;
    this.createError.set(null);
    this.createdPlanId.set(null);

    if (this.createMode() === "investigation") {
      const v = this.invForm.getRawValue();
      // disabled controls are skipped by `invalid` — check values too
      if (this.invForm.invalid || !v.investigation || !v.finding) {
        this.invForm.markAllAsTouched();
        return;
      }
      this.postPlan({
        investigation_id: v.investigation,
        finding_id: v.finding,
        title: v.title.trim() || undefined,
      });
    } else {
      if (this.manualForm.invalid) {
        this.manualForm.markAllAsTouched();
        return;
      }
      const v = this.manualForm.getRawValue();
      const recommendations = v.recommendations
        .split("\n")
        .map((r) => r.trim())
        .filter((r) => r.length > 0);
      this.postPlan({
        title: v.title.trim() || undefined,
        finding: {
          category: v.category,
          severity: v.severity,
          status: v.status,
          explanation: v.explanation.trim(),
          recommendations,
        },
      });
    }
  }

  private postPlan(body: Parameters<ApiService["createPlan"]>[0]): void {
    this.creating.set(true);
    this.api
      .createPlan(body)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.creating.set(false);
          this.createdPlanId.set(res.plan_id);
          this.refreshPlans();
        },
        error: (err: unknown) => {
          this.creating.set(false);
          this.createError.set(apiErrorDetail(err));
        },
      });
  }

  /* ---------------- lifecycle actions ---------------- */

  protected submitPlan(): void {
    const id = this.selectedPlanId();
    if (id) this.runAction("submit", () => this.api.submitPlan(id), true);
  }

  protected approvePlan(): void {
    const id = this.selectedPlanId();
    const approver = this.actionForm.controls.approver.value.trim();
    if (!id) return;
    if (!approver) {
      this.actionForm.controls.approver.markAsTouched();
      return;
    }
    this.runAction("approve", () => this.api.approvePlan(id, approver), true);
  }

  protected rejectPlan(): void {
    const id = this.selectedPlanId();
    if (!id) return;
    const reason = this.actionForm.controls.reason.value.trim();
    this.runAction("reject", () => this.api.rejectPlan(id, reason), true);
  }

  protected dryRunPlan(): void {
    const id = this.selectedPlanId();
    if (!id) return;
    this.dryRun.set(null);
    this.execResult.set(null);
    this.runAction("dry-run", () => this.api.dryRunPlan(id), false, (res) => {
      this.dryRun.set(res);
    });
  }

  protected executeLocalPlan(): void {
    const id = this.selectedPlanId();
    if (!id) return;
    this.dryRun.set(null);
    this.execResult.set(null);
    this.runAction(
      "execute-local",
      () => this.api.executeLocalPlan(id),
      false,
      (res) => this.execResult.set(res),
    );
  }

  /**
   * Run one lifecycle action. `refreshesPlan` triggers a detail+list
   * reload (state transitions); otherwise `onOk` captures the
   * action-specific payload (dry-run preview / execution results).
   * Every action response carries an optional `note` shown verbatim.
   */
  private runAction<T extends { note?: string }>(
    name: string,
    call: () => Observable<T>,
    refreshesPlan: boolean,
    onOk?: (res: T) => void,
  ): void {
    if (this.acting()) return;
    const id = this.selectedPlanId();
    if (!id) return;
    this.acting.set(name);
    this.actionError.set(null);
    this.actionNote.set(null);
    call()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.acting.set(null);
          this.actionNote.set(res.note ?? null);
          onOk?.(res);
          if (refreshesPlan) {
            this.openPlan(id);
            this.refreshPlans();
          }
        },
        error: (err: unknown) => {
          this.acting.set(null);
          this.actionError.set(apiErrorDetail(err));
        },
      });
  }

  /* ---------------- display helpers ---------------- */

  /** Badge modifier for a plan lifecycle state. */
  protected planStateClass(state: string): string {
    switch (state) {
      case "VALIDATED":
        return "status-running";
      case "AWAITING_APPROVAL":
        return "status-warn";
      case "APPROVED":
        return "status-ok";
      case "REJECTED":
        return "status-error";
      default:
        return "status-neutral";
    }
  }

  protected execStatusClass(status: string): string {
    switch (status) {
      case "APPLIED":
        return "status-ok";
      case "PENDING":
        return "status-running";
      case "BLOCKED":
      case "SKIPPED":
        return "status-warn";
      default:
        return "status-neutral";
    }
  }

  protected formatIso(iso: string | null): string {
    if (!iso) return "—";
    const d = new Date(iso);
    return Number.isNaN(d.getTime())
      ? iso
      : d.toLocaleString(this.i18n.locale());
  }

  protected paramsJson(params: Record<string, unknown>): string {
    const keys = Object.keys(params);
    return keys.length ? JSON.stringify(params) : "{}";
  }

  /** Safe render for a `result` payload of unknown shape. */
  protected jsonVal(v: unknown): string {
    return typeof v === "string" ? v : JSON.stringify(v);
  }

  protected hasLocalAction(change: ProposedChange): boolean {
    return change.local_action !== null;
  }
}
