import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from "@angular/core";

import type { CompareResponse } from "../../core/api.models";
import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { RegressionFindingsComponent } from "./regression-findings.component";

/**
 * Rendered result of POST /api/v1/history/compare (ds-0087 §8.3-8.4):
 * baseline ids vs the current snapshot, absolute/relative deltas,
 * config drift, cost deltas and regression findings — plus explicit
 * incomparability reasons and limitations. Optional fields stay
 * optional because the backend early-returns a reduced payload when
 * no baseline is eligible.
 */
@Component({
  selector: "ds-compare-result",
  standalone: true,
  imports: [TranslatePipe, RegressionFindingsComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (!result().comparable) {
      <div class="note note--warn" role="status">
        <h3>{{ "ops.cmp.notComparable" | t }}</h3>
        @if (reasons().length) {
          <ul>
            @for (r of reasons(); track r) {
              <li>{{ r }}</li>
            }
          </ul>
        }
        @if (limitations().length) {
          <h4>{{ "ops.cmp.limitations" | t }}</h4>
          <ul>
            @for (lim of limitations(); track lim) {
              <li>{{ lim }}</li>
            }
          </ul>
        }
      </div>
    } @else {
      <dl class="kv">
        <div>
          <dt>{{ "ops.cmp.current" | t }}</dt>
          <dd><code>{{ currentId() || "—" }}</code></dd>
        </div>
        <div>
          <dt>{{ "ops.cmp.baselineIds" | t }}</dt>
          <dd>
            @for (id of result().baseline_snapshot_ids ?? []; track id) {
              <code>{{ id }}</code>
            } @empty {
              <span class="muted">—</span>
            }
          </dd>
        </div>
        <div>
          <dt>{{ "ops.cmp.durationDelta" | t }}</dt>
          <dd>{{ fmtDelta(result().duration_delta_s ?? null, "s") }}</dd>
        </div>
        <div>
          <dt>{{ "ops.cmp.durationDeltaPct" | t }}</dt>
          <dd>{{ fmtPct(result().duration_delta_pct ?? null) }}</dd>
        </div>
        <div>
          <dt>{{ "ops.cmp.volumeIn" | t }}</dt>
          <dd>{{ fmtDelta(result().volume_delta_input ?? null, "B") }}</dd>
        </div>
        <div>
          <dt>{{ "ops.cmp.volumeOut" | t }}</dt>
          <dd>{{ fmtDelta(result().volume_delta_output ?? null, "B") }}</dd>
        </div>
        <div>
          <dt>{{ "ops.cmp.failureRegression" | t }}</dt>
          <dd>
            @if (result().failure_regression === true) {
              <span class="ds-badge ds-badge--status-error">
                {{ "ops.cmp.failureRegression.yes" | t }}
              </span>
            } @else if (result().failure_regression === false) {
              <span class="ds-badge ds-badge--status-ok">
                {{ "ops.cmp.failureRegression.no" | t }}
              </span>
            } @else {
              <span class="muted">—</span>
            }
          </dd>
        </div>
      </dl>

      @if (resourceRows().length) {
        <h3>{{ "ops.cmp.resourceDeltas" | t }}</h3>
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th scope="col">{{ "ops.findings.col.metric" | t }}</th>
                <th scope="col">{{ "ops.cmp.col.delta" | t }}</th>
              </tr>
            </thead>
            <tbody>
              @for (row of resourceRows(); track row[0]) {
                <tr>
                  <td><code>{{ row[0] }}</code></td>
                  <td>{{ fmtDelta(row[1], "") }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }

      @if (costRows().length) {
        <h3>{{ "ops.cmp.costDelta" | t }}</h3>
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th scope="col">{{ "ops.cmp.col.costKey" | t }}</th>
                <th scope="col">{{ "ops.cmp.col.delta" | t }}</th>
              </tr>
            </thead>
            <tbody>
              @for (row of costRows(); track row[0]) {
                <tr>
                  <td><code>{{ row[0] }}</code></td>
                  <td>{{ fmtDelta(row[1], "") }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }

      @if ((result().config_drift ?? []).length) {
        <h3>{{ "ops.cmp.configDrift" | t }}</h3>
        <ul class="str-list">
          @for (d of result().config_drift ?? []; track d) {
            <li>{{ d }}</li>
          }
        </ul>
      }

      @if ((result().quality_changes ?? []).length) {
        <h3>{{ "ops.cmp.qualityChanges" | t }}</h3>
        <ul class="str-list">
          @for (qc of result().quality_changes ?? []; track qc) {
            <li>{{ qc }}</li>
          }
        </ul>
      }

      <h3>{{ "ops.cmp.findings" | t }}</h3>
      <ds-regression-findings
        [findings]="result().regression_findings ?? []"
      />

      @if (limitations().length) {
        <div class="note" role="note">
          <h3>{{ "ops.cmp.limitations" | t }}</h3>
          <ul>
            @for (lim of limitations(); track lim) {
              <li>{{ lim }}</li>
            }
          </ul>
        </div>
      }

      @if (reasons().length) {
        <h3>{{ "ops.cmp.reasons" | t }}</h3>
        <ul class="str-list">
          @for (r of reasons(); track r) {
            <li>{{ r }}</li>
          }
        </ul>
      }
    }
  `,
  styles: `
    .muted {
      color: var(--ds-fg-muted);
    }

    .kv {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
      gap: var(--ds-space-4);
      margin: var(--ds-space-3) 0 var(--ds-space-4);
    }

    .kv dt {
      font-size: var(--ds-text-xs);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--ds-fg-subtle);
    }

    .kv dd {
      margin: var(--ds-space-1) 0 0;
      font-size: var(--ds-text-sm);
    }

    .kv dd code {
      margin-right: var(--ds-space-2);
    }

    h3 {
      font-size: var(--ds-text-sm);
      margin-top: var(--ds-space-4);
    }

    h4 {
      font-size: var(--ds-text-sm);
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: var(--ds-text-sm);
      margin-top: var(--ds-space-2);
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

    .str-list {
      margin: var(--ds-space-2) 0 0;
      padding-left: var(--ds-space-5);
      color: var(--ds-fg-muted);
      display: grid;
      gap: var(--ds-space-1);
    }

    .note {
      margin-top: var(--ds-space-4);
      border: 1px solid var(--ds-border);
      border-left: 3px solid var(--ds-warning);
      border-radius: var(--ds-radius-md);
      padding: var(--ds-space-4);
      background: var(--ds-surface-2);
    }

    .note h3 {
      margin-top: 0;
      color: var(--ds-warning);
    }

    .note ul {
      margin: var(--ds-space-2) 0 0;
      padding-left: var(--ds-space-5);
      color: var(--ds-fg-muted);
    }
  `,
})
export class CompareResultComponent {
  /** The raw compare response from the API. */
  readonly result = input.required<CompareResponse>();
  /** snapshot_id of the compared snapshot, for display. */
  readonly currentId = input<string>("");

  protected readonly reasons = computed(
    () => this.result().incomparability_reasons ?? [],
  );

  protected readonly limitations = computed(
    () => this.result().limitations ?? [],
  );

  protected readonly resourceRows = computed(() =>
    Object.entries(this.result().resource_deltas ?? {}).sort(([a], [b]) =>
      a.localeCompare(b),
    ),
  );

  protected readonly costRows = computed(() =>
    Object.entries(this.result().cost_delta ?? {}).sort(([a], [b]) =>
      a.localeCompare(b),
    ),
  );

  protected fmtDelta(v: number | null, unit: string): string {
    if (v === null || v === undefined) return "—";
    const sign = v > 0 ? "+" : "";
    const num = Number.isInteger(v) ? String(v) : v.toFixed(2);
    return `${sign}${num}${unit ? ` ${unit}` : ""}`;
  }

  protected fmtPct(v: number | null): string {
    if (v === null || v === undefined) return "—";
    const sign = v > 0 ? "+" : "";
    return `${sign}${v.toFixed(1)}%`;
  }
}
