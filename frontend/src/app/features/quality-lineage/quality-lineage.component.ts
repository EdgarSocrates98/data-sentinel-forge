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

import type {
  LineageIngestResult,
  QualityAssessResult,
  ToolManifestEntry,
} from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { observationStatusClass } from "../../shared/status-class";
import {
  acceptsSingleFile,
  analyzerSuffix,
  apiErrorDetail,
  missingInputs,
} from "../../shared/tool-manifest";
import {
  datasetLabel,
  lineageEdges,
  lineageNodes,
  parseLineageResult,
  parseQualityResult,
  scalarLabel,
} from "./quality-lineage.model";

type LoadState = "loading" | "ok" | "error";
type Tab = "quality" | "lineage";

const QUALITY_ASSESS = "sentinel.quality.assess";
const QUALITY_DRIFT = "sentinel.quality.detect_drift";
const LINEAGE_INGEST = "sentinel.lineage.ingest";
const LINEAGE_IMPACT = "sentinel.lineage.impact";

/**
 * Quality & Lineage Studio (ds-0076, spec 06.7): two tabs.
 *
 * Quality — `sentinel.quality.assess` on a local export renders the
 * real normalized observations; `sentinel.quality.detect_drift` needs
 * two file inputs while the analyze endpoint only forwards `{file}`,
 * so it is declared unavailable with its real required inputs instead
 * of a fake two-file form.
 *
 * Lineage — `sentinel.lineage.ingest` renders the dataset→dataset
 * adjacency as a node list + edges table (no new graph lib);
 * `sentinel.lineage.impact` needs a `target` input the endpoint cannot
 * forward — honest note, same treatment.
 */
@Component({
  selector: "ds-quality-lineage",
  standalone: true,
  imports: [ReactiveFormsModule, TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./quality-lineage.component.html",
  styleUrl: "./quality-lineage.component.css",
})
export class QualityLineageComponent {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);

  protected readonly toolsState = signal<LoadState>("loading");
  protected readonly tools = signal<ToolManifestEntry[]>([]);
  protected readonly tab = signal<Tab>("quality");

  protected readonly qualityRunning = signal(false);
  protected readonly qualityError = signal<string | null>(null);
  protected readonly quality = signal<QualityAssessResult | null>(null);
  protected readonly qualityFile = signal("");
  protected readonly expandedObs = signal<ReadonlySet<string>>(new Set());

  protected readonly lineageRunning = signal(false);
  protected readonly lineageError = signal<string | null>(null);
  protected readonly lineage = signal<LineageIngestResult | null>(null);
  protected readonly lineageFile = signal("");

  protected readonly qualityForm = this.fb.nonNullable.group({
    file: this.fb.nonNullable.control("", Validators.required),
  });
  protected readonly lineageForm = this.fb.nonNullable.group({
    file: this.fb.nonNullable.control("", Validators.required),
  });

  protected readonly observationStatusClass = observationStatusClass;
  protected readonly datasetLabel = datasetLabel;
  protected readonly scalarLabel = scalarLabel;

  /** File-compatible flag for a given registry tool id. */
  protected toolAvailable(toolId: string): boolean {
    const t = this.tools().find((x) => x.name === toolId);
    return !!t && acceptsSingleFile(t);
  }

  /** Inputs a tool needs beyond `{file}` — for honest notes. */
  protected toolMissingInputs(toolId: string): string[] {
    const t = this.tools().find((x) => x.name === toolId);
    return t ? missingInputs(t) : [];
  }

  protected toolRegistered(toolId: string): boolean {
    return this.tools().some((x) => x.name === toolId);
  }

  protected readonly toolIds = {
    assess: QUALITY_ASSESS,
    drift: QUALITY_DRIFT,
    ingest: LINEAGE_INGEST,
    impact: LINEAGE_IMPACT,
  } as const;

  protected readonly edges = computed(() =>
    lineageEdges(this.lineage()?.downstream ?? {}),
  );
  protected readonly nodes = computed(() =>
    lineageNodes(this.lineage()?.downstream ?? {}),
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
      },
      error: () => {
        this.tools.set([]);
        this.toolsState.set("error");
      },
    });
  }

  protected selectTab(tab: Tab): void {
    this.tab.set(tab);
  }

  /** ARIA tablist keyboard nav: arrows move focus across tabs. */
  protected onTabKeydown(event: KeyboardEvent): void {
    const tabs = ["quality", "lineage"] as const;
    const current = tabs.indexOf(this.tab());
    let next = current;
    if (event.key === "ArrowRight") {
      next = (current + 1) % tabs.length;
    } else if (event.key === "ArrowLeft") {
      next = (current - 1 + tabs.length) % tabs.length;
    } else if (event.key === "Home") {
      next = 0;
    } else if (event.key === "End") {
      next = tabs.length - 1;
    } else {
      return;
    }
    event.preventDefault();
    this.selectTab(tabs[next]);
    const el = (event.target as HTMLElement)
      .closest('[role="tablist"]')
      ?.querySelectorAll<HTMLElement>('[role="tab"]')
      .item(next);
    el?.focus();
  }

  protected runQuality(): void {
    if (this.qualityForm.invalid || this.qualityRunning()) {
      this.qualityForm.markAllAsTouched();
      return;
    }
    const file = this.qualityForm.getRawValue().file;
    this.qualityRunning.set(true);
    this.qualityError.set(null);
    this.api.analyze(analyzerSuffix(QUALITY_ASSESS), file).subscribe({
      next: (payload) => {
        this.qualityRunning.set(false);
        this.qualityFile.set(file);
        this.quality.set(parseQualityResult(payload));
        this.expandedObs.set(new Set());
      },
      error: (err: unknown) => {
        this.qualityRunning.set(false);
        this.quality.set(null);
        this.qualityError.set(apiErrorDetail(err));
      },
    });
  }

  protected runLineage(): void {
    if (this.lineageForm.invalid || this.lineageRunning()) {
      this.lineageForm.markAllAsTouched();
      return;
    }
    const file = this.lineageForm.getRawValue().file;
    this.lineageRunning.set(true);
    this.lineageError.set(null);
    this.api.analyze(analyzerSuffix(LINEAGE_INGEST), file).subscribe({
      next: (payload) => {
        this.lineageRunning.set(false);
        this.lineageFile.set(file);
        this.lineage.set(parseLineageResult(payload));
      },
      error: (err: unknown) => {
        this.lineageRunning.set(false);
        this.lineage.set(null);
        this.lineageError.set(apiErrorDetail(err));
      },
    });
  }

  protected hasObsDetail(o: {
    rule_id: string;
    run_id: string;
    provenance: string;
    limitations: string[];
  }): boolean {
    return !!(o.rule_id || o.run_id || o.provenance || o.limitations.length);
  }

  protected toggleObs(id: string): void {
    this.expandedObs.update((set) => {
      const next = new Set(set);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }
}
