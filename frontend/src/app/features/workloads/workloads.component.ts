import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from "@angular/core";
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from "@angular/forms";

import type { ToolManifestEntry } from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import {
  type AnalysisResult,
  countBy,
  normalizeAnalysisResult,
} from "../../shared/analysis-result";
import { AnalysisResultComponent } from "../../shared/analysis-result/analysis-result.component";
import {
  acceptsSingleFile,
  analyzerSuffix,
  apiErrorDetail,
  missingInputs,
} from "../../shared/tool-manifest";

type LoadState = "loading" | "ok" | "error";

/**
 * File-input tool families surfaced in the workload explorer (spec
 * 06.5). EMR tools are also reachable through the guided platform
 * selector below; `sentinel.emr.estimate_cost` is intentionally absent
 * because it is not file-compatible (declared honestly in the EMR
 * card). `lakehouse`/`cloudwatch` are included because they are real
 * file-based workload analyzers in the registry.
 */
const WORKLOAD_PREFIXES = [
  "sentinel.glue.",
  "sentinel.emr.",
  "sentinel.spark.",
  "sentinel.sql.",
  "sentinel.iceberg.",
  "sentinel.lakeformation.",
  "sentinel.lakehouse.",
  "sentinel.iam.",
  "sentinel.cloudwatch.",
];

/** EMR platform selector → registry analyzer (spec 06.5 §7.2-7.4). */
const EMR_PLATFORMS = [
  { id: "ec2", toolId: "sentinel.emr.analyze_ec2" },
  { id: "serverless", toolId: "sentinel.emr.analyze_serverless" },
  { id: "eks", toolId: "sentinel.emr.analyze_eks" },
] as const;

const EMR_COST_TOOL = "sentinel.emr.estimate_cost";

/** One row of the cross-result differences table. */
interface CompareRow {
  /** i18n key for the row label. */
  labelKey: string;
  /** Literal suffix (e.g. the severity/status value). */
  suffix: string;
  values: string[];
  differs: boolean;
}

/**
 * Workload Explorer (ds-0075, spec 06.5): file-based analysis through
 * `POST /api/v1/analyze/{id}` for the Glue/EMR/Spark/SQL/Iceberg/
 * LakeFormation/IAM tool families, a guided EMR platform selector, an
 * honest note for the non-file cost estimator, and a descriptive
 * cross-result comparison of result sets obtained in-session.
 */
@Component({
  selector: "ds-workloads",
  standalone: true,
  imports: [ReactiveFormsModule, TranslatePipe, AnalysisResultComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./workloads.component.html",
  styleUrl: "./workloads.component.css",
})
export class WorkloadsComponent {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);

  protected readonly toolsState = signal<LoadState>("loading");
  protected readonly tools = signal<ToolManifestEntry[]>([]);

  protected readonly running = signal(false);
  protected readonly analyzeError = signal<string | null>(null);

  /** All results obtained in this session (comparison candidates). */
  protected readonly results = signal<AnalysisResult[]>([]);
  /** Indexes of `results()` selected for side-by-side comparison. */
  protected readonly compareSel = signal<ReadonlySet<number>>(new Set());

  protected readonly emrPlatform = signal<string>(EMR_PLATFORMS[0].id);

  protected readonly form = this.fb.nonNullable.group({
    tool: this.fb.nonNullable.control("", Validators.required),
    file: this.fb.nonNullable.control("", Validators.required),
  });
  protected readonly emrForm = this.fb.nonNullable.group({
    file: this.fb.nonNullable.control("", Validators.required),
  });

  /** Manifest tools callable via `POST /analyze/{id}` in this page. */
  protected readonly workloadTools = computed(() =>
    this.tools().filter(
      (t) =>
        acceptsSingleFile(t) &&
        WORKLOAD_PREFIXES.some((p) => t.name.startsWith(p)),
    ),
  );

  /** EMR platform options with live availability from the manifest. */
  protected readonly emrPlatforms = computed(() =>
    EMR_PLATFORMS.map((p) => {
      const tool = this.tools().find((t) => t.name === p.toolId);
      return { ...p, available: !!tool && acceptsSingleFile(tool) };
    }),
  );

  /** Whether the currently selected EMR platform is file-compatible. */
  protected readonly emrPlatformAvailable = computed(
    () =>
      this.emrPlatforms().find((p) => p.id === this.emrPlatform())
        ?.available === true,
  );

  /**
   * The cost-estimation tool, when the registry exposes it. It is not
   * file-compatible — the template renders an honest note instead of a
   * form that could never succeed.
   */
  protected readonly emrCostTool = computed(
    () => this.tools().find((t) => t.name === EMR_COST_TOOL) ?? null,
  );

  protected readonly emrCostMissing = computed(() => {
    const tool = this.emrCostTool();
    return tool ? missingInputs(tool) : [];
  });

  protected readonly selectedResults = computed(() =>
    [...this.compareSel()]
      .sort((a, b) => a - b)
      .map((i) => this.results()[i])
      .filter((r): r is AnalysisResult => !!r),
  );

  /**
   * Descriptive differences table — only real fields from the stored
   * payloads, never a verdict about which modality is better.
   */
  protected readonly compareRows = computed<CompareRow[]>(() => {
    const sel = this.selectedResults();
    if (sel.length < 2) return [];
    const rows: CompareRow[] = [];
    const push = (labelKey: string, suffix: string, values: string[]) =>
      rows.push({ labelKey, suffix, values, differs: new Set(values).size > 1 });

    push("workloads.compare.tool", "", sel.map((r) => r.label));
    push("workloads.compare.file", "", sel.map((r) => r.file));
    push(
      "workloads.compare.findingsTotal",
      "",
      sel.map((r) => String(r.findings.length)),
    );
    const sevKeys = new Set<string>();
    const statusKeys = new Set<string>();
    for (const r of sel) {
      for (const [k] of countBy(r.findings, "severity")) sevKeys.add(k);
      for (const [k] of countBy(r.findings, "status")) statusKeys.add(k);
    }
    for (const k of [...sevKeys].sort()) {
      push(
        "workloads.compare.severityPrefix",
        k,
        sel.map(
          (r) =>
            String(
              countBy(r.findings, "severity").find(([key]) => key === k)?.[1] ??
                0,
            ),
        ),
      );
    }
    for (const k of [...statusKeys].sort()) {
      push(
        "workloads.compare.statusPrefix",
        k,
        sel.map(
          (r) =>
            String(
              countBy(r.findings, "status").find(([key]) => key === k)?.[1] ??
                0,
            ),
        ),
      );
    }
    push(
      "workloads.compare.limitations",
      "",
      sel.map((r) => String(r.limitations.length)),
    );
    return rows;
  });

  constructor() {
    this.loadTools();
  }

  protected loadTools(): void {
    this.toolsState.set("loading");
    this.api.tools().subscribe({
      next: (tools) => {
        this.tools.set(tools);
        this.toolsState.set("ok");
      },
      error: () => {
        this.tools.set([]);
        this.toolsState.set("error");
      },
    });
  }

  protected toolDescription(name: string): string | null {
    return this.tools().find((t) => t.name === name)?.description ?? null;
  }

  /** Run the generic workload analyzer (`{tool, file}` form). */
  protected runAnalysis(): void {
    if (this.form.invalid || this.running()) {
      this.form.markAllAsTouched();
      return;
    }
    const { tool, file } = this.form.getRawValue();
    this.execute(tool, file);
  }

  /** Run the EMR analyzer bound to the selected platform. */
  protected runEmrAnalysis(): void {
    if (this.emrForm.invalid || this.running()) {
      this.emrForm.markAllAsTouched();
      return;
    }
    const platform = EMR_PLATFORMS.find((p) => p.id === this.emrPlatform());
    if (!platform) return;
    this.execute(platform.toolId, this.emrForm.getRawValue().file);
  }

  private execute(toolId: string, file: string): void {
    this.running.set(true);
    this.analyzeError.set(null);
    this.api.analyze(analyzerSuffix(toolId), file).subscribe({
      next: (payload) => {
        this.running.set(false);
        const result = normalizeAnalysisResult(toolId, file, payload);
        this.results.update((all) => [...all, result]);
      },
      error: (err: unknown) => {
        this.running.set(false);
        this.analyzeError.set(apiErrorDetail(err));
      },
    });
  }

  protected toggleCompare(index: number): void {
    this.compareSel.update((set) => {
      const next = new Set(set);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }
}
