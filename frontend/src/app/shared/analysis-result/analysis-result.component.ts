import {
  ChangeDetectionStrategy,
  Component,
  input,
  signal,
} from "@angular/core";

import { TranslatePipe } from "../../core/i18n/translate.pipe";
import {
  confidenceClass,
  severityClass,
} from "../status-class";
import type { AnalysisResult } from "../analysis-result";

/**
 * Renders a normalized `POST /api/v1/analyze/{id}` result: scalar
 * metadata, summary, findings (severity/status badges + expandable
 * detail rows) and declared limitations. Presentational only — the
 * parent owns the API call and the payload.
 */
@Component({
  selector: "ds-analysis-result",
  standalone: true,
  imports: [TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (result(); as res) {
      <div class="result-meta">
        <p class="muted result-file">
          <code>{{ res.label }}</code> — <code>{{ res.file }}</code>
        </p>
        @if (res.extras.length) {
          <dl class="kv">
            @for (kv of res.extras; track kv[0]) {
              <div>
                <dt>{{ kv[0] }}</dt>
                <dd>{{ kv[1] }}</dd>
              </div>
            }
          </dl>
        }
        @if (res.summary) {
          <p class="summary">{{ res.summary }}</p>
        }
      </div>

      @if (res.findings.length === 0) {
        <p class="muted">{{ "analysis.noFindings" | t }}</p>
      } @else {
        <table class="data-table">
          <caption class="sr-only">{{ "analysis.findingsCaption" | t }}</caption>
          <thead>
            <tr>
              <th scope="col">{{ "analysis.col.severity" | t }}</th>
              <th scope="col">{{ "analysis.col.status" | t }}</th>
              <th scope="col">{{ "analysis.col.category" | t }}</th>
              <th scope="col">{{ "analysis.col.explanation" | t }}</th>
              <th scope="col">{{ "analysis.col.evidence" | t }}</th>
              <th scope="col">
                <span class="sr-only">{{ "analysis.expand" | t }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            @for (f of res.findings; track f.id) {
              <tr>
                <td>
                  <span
                    class="ds-badge"
                    [class]="'ds-badge ds-badge--' + severityClass(f.severity)"
                  >
                    {{ f.severity }}
                  </span>
                </td>
                <td>
                  <span
                    class="ds-badge"
                    [class]="'ds-badge ds-badge--' + confidenceClass(f.status)"
                  >
                    {{ f.status }}
                  </span>
                </td>
                <td><code>{{ f.category || "—" }}</code></td>
                <td class="explanation">{{ f.explanation }}</td>
                <td>{{ f.evidenceIds.length }}</td>
                <td>
                  @if (hasDetail(f)) {
                    <button
                      type="button"
                      class="ds-btn expand-btn"
                      (click)="toggle(f.id)"
                      [attr.aria-expanded]="expanded().has(f.id)"
                      [attr.aria-controls]="idPrefix() + '-fd-' + f.id"
                    >
                      {{
                        (expanded().has(f.id)
                          ? "analysis.collapse"
                          : "analysis.expand"
                        ) | t
                      }}
                    </button>
                  }
                </td>
              </tr>
              @if (expanded().has(f.id) && hasDetail(f)) {
                <tr class="detail-row" [id]="idPrefix() + '-fd-' + f.id">
                  <td colspan="6">
                    @if (f.evidenceIds.length) {
                      <h4>{{ "analysis.evidenceIds" | t }}</h4>
                      <ul class="inline-list">
                        @for (e of f.evidenceIds; track e) {
                          <li><code>{{ e }}</code></li>
                        }
                      </ul>
                    }
                    @if (f.recommendations.length) {
                      <h4>{{ "analysis.recommendations" | t }}</h4>
                      <ul>
                        @for (r of f.recommendations; track r) {
                          <li>{{ r }}</li>
                        }
                      </ul>
                    }
                    @if (f.validationSteps.length) {
                      <h4>{{ "analysis.validationSteps" | t }}</h4>
                      <ul>
                        @for (s of f.validationSteps; track s) {
                          <li>{{ s }}</li>
                        }
                      </ul>
                    }
                    @if (f.alternatives.length) {
                      <h4>{{ "analysis.alternatives" | t }}</h4>
                      <ul>
                        @for (a of f.alternatives; track a) {
                          <li>{{ a }}</li>
                        }
                      </ul>
                    }
                  </td>
                </tr>
              }
            }
          </tbody>
        </table>
      }

      @if (res.limitations.length) {
        <div class="limitations">
          <h4>{{ "analysis.limitations" | t }}</h4>
          <ul>
            @for (lim of res.limitations; track lim) {
              <li>{{ lim }}</li>
            }
          </ul>
        </div>
      }
    }
  `,
  styles: `
    :host {
      display: block;
      min-width: 0;
    }

    .result-meta {
      display: grid;
      gap: var(--ds-space-3);
      margin-bottom: var(--ds-space-4);
    }

    .result-file {
      margin: 0;
      overflow-wrap: anywhere;
    }

    .muted {
      color: var(--ds-fg-muted);
    }

    .summary {
      margin: 0;
      font-size: var(--ds-text-sm);
      color: var(--ds-fg);
    }

    .kv {
      margin: 0;
      display: grid;
      gap: var(--ds-space-1);
    }

    .kv > div {
      display: flex;
      justify-content: space-between;
      gap: var(--ds-space-4);
    }

    .kv dt {
      color: var(--ds-fg-muted);
      font-size: var(--ds-text-sm);
    }

    .kv dd {
      margin: 0;
      font-variant-numeric: tabular-nums;
      overflow-wrap: anywhere;
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: var(--ds-text-sm);
    }

    .data-table th {
      text-align: left;
      color: var(--ds-fg-subtle);
      font-size: var(--ds-text-xs);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: var(--ds-space-2) var(--ds-space-3);
      border-bottom: 1px solid var(--ds-border-strong);
    }

    .data-table td {
      padding: var(--ds-space-3);
      border-bottom: 1px solid var(--ds-border);
      vertical-align: top;
    }

    .data-table .explanation {
      max-width: 32rem;
    }

    .detail-row td {
      background: var(--ds-surface-2);
    }

    .detail-row h4 {
      font-size: var(--ds-text-xs);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--ds-fg-subtle);
      margin: var(--ds-space-3) 0 var(--ds-space-1);
    }

    .detail-row ul {
      margin: 0;
      padding-left: var(--ds-space-5);
      color: var(--ds-fg-muted);
    }

    .inline-list {
      list-style: none;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: var(--ds-space-2);
    }

    .expand-btn {
      padding: var(--ds-space-1) var(--ds-space-3);
      font-size: var(--ds-text-xs);
    }

    .limitations {
      margin-top: var(--ds-space-4);
    }

    .limitations h4 {
      font-size: var(--ds-text-xs);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--ds-warning);
      margin: 0 0 var(--ds-space-2);
    }

    .limitations ul {
      margin: 0;
      padding-left: var(--ds-space-5);
      color: var(--ds-fg-muted);
    }
  `,
})
export class AnalysisResultComponent {
  /** The normalized result to render. */
  readonly result = input.required<AnalysisResult>();
  /** Unique prefix for aria-controls ids (multiple results per page). */
  readonly idPrefix = input<string>("ar");

  protected readonly severityClass = severityClass;
  protected readonly confidenceClass = confidenceClass;
  protected readonly expanded = signal<ReadonlySet<string>>(new Set());

  protected hasDetail(f: {
    evidenceIds: string[];
    recommendations: string[];
    validationSteps: string[];
    alternatives: string[];
  }): boolean {
    return (
      f.evidenceIds.length > 0 ||
      f.recommendations.length > 0 ||
      f.validationSteps.length > 0 ||
      f.alternatives.length > 0
    );
  }

  protected toggle(id: string): void {
    this.expanded.update((set) => {
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
