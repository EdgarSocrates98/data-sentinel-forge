import {
  ChangeDetectionStrategy,
  Component,
  input,
} from "@angular/core";

import type { RegressionFinding } from "../../core/api.models";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { confidenceClass } from "../../shared/status-class";

/**
 * Regression findings table (ds-0087 §8.4): renders the real
 * `detect_regressions` payload — metric, baseline, current, magnitude,
 * method, z-score, confidence and causal label. Findings are labeled
 * signals (`suspected_cause`), never asserted root causes; per-finding
 * limitations are shown verbatim.
 */
@Component({
  selector: "ds-regression-findings",
  standalone: true,
  imports: [TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (findings().length === 0) {
      <p class="muted">{{ "ops.findings.none" | t }}</p>
    } @else {
      <div class="table-scroll">
        <table class="data-table findings-table">
          <caption>
            {{ "ops.findings.caption" | t }}
          </caption>
          <thead>
            <tr>
              <th scope="col">{{ "ops.findings.col.metric" | t }}</th>
              <th scope="col">{{ "ops.findings.col.baseline" | t }}</th>
              <th scope="col">{{ "ops.findings.col.current" | t }}</th>
              <th scope="col">{{ "ops.findings.col.magnitude" | t }}</th>
              <th scope="col">{{ "ops.findings.col.method" | t }}</th>
              <th scope="col">{{ "ops.findings.col.confidence" | t }}</th>
              <th scope="col">{{ "ops.findings.col.rationale" | t }}</th>
            </tr>
          </thead>
          <tbody>
            @for (f of findings(); track trackFinding(f)) {
              <tr>
                <td><code>{{ f.metric }}</code></td>
                <td>{{ fmt(f.baseline) }}</td>
                <td>{{ fmt(f.current_value) }}</td>
                <td>
                  {{ fmt(f.magnitude) }}
                  @if (f.magnitude_pct !== null) {
                    <span class="muted"> ({{ fmtPct(f.magnitude_pct) }})</span>
                  }
                  @if (f.z_score !== null) {
                    <br /><span class="muted">z={{ fmt(f.z_score) }}</span>
                  }
                </td>
                <td><code>{{ f.method }}</code></td>
                <td>
                  <span
                    class="ds-badge"
                    [class]="
                      'ds-badge ds-badge--' + confidenceClass(f.confidence)
                    "
                  >
                    {{ f.confidence }}
                  </span>
                  <br />
                  <span class="muted small">{{ f.causal_label }}</span>
                </td>
                <td>
                  {{ f.rationale }}
                  @if (f.limitations.length) {
                    <ul class="lim-list">
                      @for (lim of f.limitations; track lim) {
                        <li>{{ lim }}</li>
                      }
                    </ul>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <p class="muted small">{{ "ops.findings.causalNote" | t }}</p>
    }
  `,
  styles: `
    .muted {
      color: var(--ds-fg-muted);
    }

    .small {
      font-size: var(--ds-text-xs);
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: var(--ds-text-sm);
      margin-top: var(--ds-space-3);
    }

    .data-table caption {
      text-align: left;
      color: var(--ds-fg-subtle);
      font-size: var(--ds-text-xs);
      padding-bottom: var(--ds-space-2);
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
      padding: var(--ds-space-2) var(--ds-space-3);
      border-bottom: 1px solid var(--ds-border);
      vertical-align: top;
    }

    .lim-list {
      margin: var(--ds-space-2) 0 0;
      padding-left: var(--ds-space-4);
      color: var(--ds-fg-subtle);
      font-size: var(--ds-text-xs);
    }
  `,
})
export class RegressionFindingsComponent {
  readonly findings = input.required<RegressionFinding[]>();

  protected readonly confidenceClass = confidenceClass;

  /** Identity for @for — findings carry no id field. */
  protected trackFinding(f: RegressionFinding): string {
    return `${f.metric}|${f.method}|${f.baseline}|${f.current_value}`;
  }

  protected fmt(v: number | null): string {
    if (v === null || v === undefined) return "—";
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }

  protected fmtPct(v: number | null): string {
    if (v === null) return "—";
    const sign = v > 0 ? "+" : "";
    return `${sign}${v.toFixed(1)}%`;
  }
}
