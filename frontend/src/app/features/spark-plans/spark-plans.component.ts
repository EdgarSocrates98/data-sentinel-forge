import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from "@angular/core";
import { NgTemplateOutlet } from "@angular/common";
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
  normalizeAnalysisResult,
} from "../../shared/analysis-result";
import { AnalysisResultComponent } from "../../shared/analysis-result/analysis-result.component";
import {
  acceptsSingleFile,
  analyzerSuffix,
  apiErrorDetail,
} from "../../shared/tool-manifest";

type LoadState = "loading" | "ok" | "error";

/** Spark tool family — analyze_plan first, optimize when present. */
const SPARK_PREFIX = "sentinel.spark.";

/** Candidate payload keys that may carry a plan/operator tree. */
const TREE_KEYS = ["plan_tree", "tree", "stages", "nodes", "plan"];
const CHILD_KEYS = ["children", "stages", "nodes"];
const MAX_DEPTH = 16;

/** One node of a structured plan tree, when the payload carries one. */
export interface PlanTreeNode {
  label: string;
  children: PlanTreeNode[];
}

type PlanTree =
  | { kind: "nodes"; nodes: PlanTreeNode[] }
  | { kind: "text"; text: string }
  | null;

function isRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function nodeLabel(v: Record<string, unknown>): string {
  for (const k of ["name", "operator", "label", "id", "stage_id", "node"]) {
    const val = v[k];
    if (typeof val === "string" || typeof val === "number") {
      return String(val);
    }
  }
  const scalar = Object.entries(v)
    .filter(
      ([k, val]) =>
        !CHILD_KEYS.includes(k) &&
        (typeof val === "string" ||
          typeof val === "number" ||
          typeof val === "boolean"),
    )
    .map(([k, val]) => `${k}=${String(val)}`)
    .join(", ");
  return scalar || JSON.stringify(v).slice(0, 120);
}

function toNode(v: unknown, depth: number): PlanTreeNode | null {
  if (depth > MAX_DEPTH) return null;
  if (typeof v === "string" || typeof v === "number") {
    return { label: String(v), children: [] };
  }
  if (!isRecord(v)) return null;
  const children: PlanTreeNode[] = [];
  for (const key of CHILD_KEYS) {
    const raw = v[key];
    if (Array.isArray(raw)) {
      for (const c of raw) {
        const n = toNode(c, depth + 1);
        if (n) children.push(n);
      }
    }
  }
  return { label: nodeLabel(v), children };
}

/**
 * Look for a structured plan tree in the payload. Diagnostics-backed
 * tools currently emit `{report_id, findings, summary, limitations}` —
 * no tree — so this returns null today and the findings table is the
 * honest rendering. If a future payload carries one of TREE_KEYS it is
 * rendered indented without any UI change.
 */
export function extractPlanTree(payload: unknown): PlanTree {
  if (!isRecord(payload)) return null;
  for (const key of TREE_KEYS) {
    const raw = payload[key];
    if (raw === undefined || raw === null) continue;
    if (typeof raw === "string" && raw.trim()) {
      return { kind: "text", text: raw };
    }
    if (Array.isArray(raw)) {
      const nodes = raw
        .map((v) => toNode(v, 0))
        .filter((n): n is PlanTreeNode => n !== null);
      if (nodes.length) return { kind: "nodes", nodes };
    }
    if (isRecord(raw)) {
      const n = toNode(raw, 0);
      if (n) return { kind: "nodes", nodes: [n] };
    }
  }
  return null;
}

/**
 * Spark Execution Plan Explorer (ds-0075, spec 06.6): submits a local
 * plan/artifact file to `sentinel.spark.*` file tools via
 * `POST /api/v1/analyze/{id}` and renders the real response — a plan
 * tree when the payload carries one, otherwise the findings table.
 * Honest empty state before the first run; API-down is explicit.
 */
@Component({
  selector: "ds-spark-plans",
  standalone: true,
  imports: [
    NgTemplateOutlet,
    ReactiveFormsModule,
    TranslatePipe,
    AnalysisResultComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./spark-plans.component.html",
  styleUrl: "./spark-plans.component.css",
})
export class SparkPlansComponent {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);

  protected readonly toolsState = signal<LoadState>("loading");
  protected readonly tools = signal<ToolManifestEntry[]>([]);
  protected readonly running = signal(false);
  protected readonly analyzeError = signal<string | null>(null);
  protected readonly result = signal<AnalysisResult | null>(null);
  protected readonly planTree = signal<PlanTree>(null);

  protected readonly form = this.fb.nonNullable.group({
    tool: this.fb.nonNullable.control("", Validators.required),
    file: this.fb.nonNullable.control("", Validators.required),
  });

  /** File-compatible Spark tools exposed by the live manifest. */
  protected readonly sparkTools = computed(() =>
    this.tools().filter(
      (t) => acceptsSingleFile(t) && t.name.startsWith(SPARK_PREFIX),
    ),
  );

  constructor() {
    this.loadTools();
  }

  protected loadTools(): void {
    this.toolsState.set("loading");
    this.api.tools().subscribe({
      next: (tools) => {
        this.tools.set(tools);
        this.toolsState.set("ok");
        const first = this.sparkTools().find(
          (t) => t.name === "sentinel.spark.analyze_plan",
        ) ?? this.sparkTools()[0];
        if (first && !this.form.controls.tool.value) {
          this.form.controls.tool.setValue(first.name);
        }
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

  protected runAnalysis(): void {
    if (this.form.invalid || this.running()) {
      this.form.markAllAsTouched();
      return;
    }
    const { tool, file } = this.form.getRawValue();
    this.running.set(true);
    this.analyzeError.set(null);
    this.api.analyze(analyzerSuffix(tool), file).subscribe({
      next: (payload) => {
        this.running.set(false);
        this.planTree.set(extractPlanTree(payload));
        this.result.set(normalizeAnalysisResult(tool, file, payload));
      },
      error: (err: unknown) => {
        this.running.set(false);
        this.result.set(null);
        this.planTree.set(null);
        this.analyzeError.set(apiErrorDetail(err));
      },
    });
  }
}
