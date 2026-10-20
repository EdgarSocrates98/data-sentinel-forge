import { ChangeDetectionStrategy, Component, input } from "@angular/core";

import { TranslatePipe } from "../../core/i18n/translate.pipe";

/**
 * Real placeholder page for routes whose studio ships in a later phase.
 * Renders a proper page layout (header, lead, planned capabilities,
 * under-construction badge) — never fake functionality or lorem ipsum.
 */
@Component({
  selector: "ds-page-shell",
  standalone: true,
  imports: [TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <article class="page" aria-labelledby="page-title">
      <header class="page-header">
        <div class="page-header-text">
          <h1 id="page-title">{{ titleKey() | t }}</h1>
          <p class="lead">{{ leadKey() | t }}</p>
        </div>
        <span class="ds-badge ds-badge--wip">
          {{ "status.underConstruction" | t }}
        </span>
      </header>

      <section class="ds-card panel" aria-labelledby="planned-heading">
        <h2 id="planned-heading">{{ "status.plannedCapabilities" | t }}</h2>
        <ul class="planned-list">
          @for (key of plannedKeys(); track key) {
            <li>{{ key | t }}</li>
          }
        </ul>
      </section>
    </article>
  `,
  styles: `
    .page {
      display: flex;
      flex-direction: column;
      gap: var(--ds-space-6);
      max-width: 60rem;
    }

    .page-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: var(--ds-space-4);
      flex-wrap: wrap;
    }

    h1 {
      font-size: var(--ds-text-2xl);
    }

    .lead {
      color: var(--ds-fg-muted);
      font-size: var(--ds-text-lg);
      line-height: var(--ds-p-leading-relaxed);
      max-width: 48rem;
    }

    .panel {
      padding: var(--ds-space-6);
    }

    .panel h2 {
      font-size: var(--ds-text-lg);
      color: var(--ds-fg);
    }

    .planned-list {
      margin: 0;
      padding-left: var(--ds-space-5);
      color: var(--ds-fg-muted);
      display: grid;
      gap: var(--ds-space-2);
    }

    .planned-list li::marker {
      color: var(--ds-accent);
    }
  `,
})
export class PageShellComponent {
  /** i18n key for the <h1> title. */
  readonly titleKey = input.required<string>();
  /** i18n key for the lead paragraph. */
  readonly leadKey = input.required<string>();
  /** i18n keys listing the planned capabilities (real roadmap items). */
  readonly plannedKeys = input.required<readonly string[]>();
}
