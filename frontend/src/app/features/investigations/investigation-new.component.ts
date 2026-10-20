import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from "@angular/core";
import {
  FormArray,
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from "@angular/forms";
import { Router, RouterLink } from "@angular/router";

import type { ToolManifestEntry } from "../../core/api.models";
import { ApiService } from "../../core/api.service";
import { TranslatePipe } from "../../core/i18n/translate.pipe";

const PROBLEM_MAX = 4000;

interface FileRowValue {
  tool_id: string;
  path: string;
}

type ToolsState = "loading" | "ok" | "error";

/**
 * New-investigation form (ds-0073 §5.1-5.2): problem statement plus
 * optional local file inputs, each bound to a real tool from
 * GET /api/v1/tools. Only tools whose manifest accepts a single `file`
 * input are offered — the investigations endpoint executes
 * `{tool_id: path}` pairs and non-file tools would fail honestly.
 */
@Component({
  selector: "ds-investigation-new",
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./investigation-new.component.html",
  styleUrl: "./investigation-new.component.css",
})
export class InvestigationNewComponent {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);

  protected readonly problemMax = PROBLEM_MAX;
  protected readonly toolsState = signal<ToolsState>("loading");
  protected readonly tools = signal<ToolManifestEntry[]>([]);
  protected readonly submitting = signal(false);
  protected readonly submitError = signal<string | null>(null);
  protected readonly duplicateToolError = signal(false);

  protected readonly form = this.fb.nonNullable.group({
    problem: this.fb.nonNullable.control("", [
      Validators.required,
      Validators.maxLength(PROBLEM_MAX),
    ]),
    files: this.fb.nonNullable.array(
      [] as ReturnType<typeof this.newFileRow>[],
    ),
  });

  /** Manifest entries usable as `{tool_id: path}` file inputs. */
  protected readonly fileTools = computed(() =>
    this.tools().filter((t) => acceptsSingleFile(t)),
  );

  constructor() {
    this.loadTools();
  }

  get files(): FormArray {
    return this.form.controls.files;
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

  protected addFileRow(): void {
    this.files.push(this.newFileRow());
  }

  protected removeFileRow(index: number): void {
    this.files.removeAt(index);
    this.duplicateToolError.set(false);
  }

  private newFileRow() {
    return this.fb.nonNullable.group({
      tool_id: this.fb.nonNullable.control("", Validators.required),
      path: this.fb.nonNullable.control("", Validators.required),
    });
  }

  protected problemLength(): number {
    return this.form.controls.problem.value.length;
  }

  /** Manifest description for the selected tool id, if any. */
  protected toolDescription(toolId: string | undefined): string | null {
    if (!toolId) return null;
    return this.tools().find((t) => t.name === toolId)?.description ?? null;
  }

  protected submit(): void {
    this.duplicateToolError.set(false);
    if (this.form.invalid || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }
    const rows = this.files.getRawValue() as FileRowValue[];
    const seen = new Set<string>();
    const files: Record<string, string> = {};
    for (const row of rows) {
      if (seen.has(row.tool_id)) {
        this.duplicateToolError.set(true);
        return;
      }
      seen.add(row.tool_id);
      files[row.tool_id] = row.path;
    }

    this.submitting.set(true);
    this.submitError.set(null);
    this.api
      .createInvestigation({
        problem: this.form.controls.problem.value,
        files,
      })
      .subscribe({
        next: (res) => {
          this.submitting.set(false);
          void this.router.navigate([
            "/investigations",
            res.investigation_id,
          ]);
        },
        error: (err: { detail?: string | null }) => {
          this.submitting.set(false);
          this.submitError.set(err.detail ?? null);
        },
      });
  }
}

/** A manifest entry is file-compatible when `file` covers its inputs. */
function acceptsSingleFile(tool: ToolManifestEntry): boolean {
  const schema = tool.inputSchema;
  const required = Array.isArray(schema["required"])
    ? (schema["required"] as unknown[])
    : [];
  const properties =
    schema["properties"] && typeof schema["properties"] === "object"
      ? (schema["properties"] as Record<string, unknown>)
      : {};
  return required.every((r) => r === "file") && "file" in properties;
}
