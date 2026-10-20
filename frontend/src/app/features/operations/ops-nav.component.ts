import { ChangeDetectionStrategy, Component } from "@angular/core";
import { RouterLink, RouterLinkActive } from "@angular/router";

import { TranslatePipe } from "../../core/i18n/translate.pipe";

interface OpsNavItem {
  path: string;
  labelKey: string;
  exact: boolean;
}

/**
 * Tab bar shared by every Operations page (ds-0087 §8) — links to the
 * five operations views. `aria-current="page"` mirrors the active
 * route for assistive technologies.
 */
@Component({
  selector: "ds-ops-nav",
  standalone: true,
  imports: [RouterLink, RouterLinkActive, TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nav class="ops-nav" [attr.aria-label]="'ops.nav.label' | t">
      <ul>
        @for (item of items; track item.path) {
          <li>
            <a
              [routerLink]="item.path"
              routerLinkActive="active"
              #rla="routerLinkActive"
              [routerLinkActiveOptions]="{ exact: item.exact }"
              [attr.aria-current]="rla.isActive ? 'page' : null"
            >
              {{ item.labelKey | t }}
            </a>
          </li>
        }
      </ul>
    </nav>
  `,
  styles: `
    .ops-nav ul {
      display: flex;
      flex-wrap: wrap;
      gap: var(--ds-space-2);
      list-style: none;
      margin: 0;
      padding: 0;
      border-bottom: 1px solid var(--ds-border);
    }

    .ops-nav a {
      display: inline-flex;
      padding: var(--ds-space-2) var(--ds-space-4);
      font-size: var(--ds-text-sm);
      font-weight: var(--ds-p-weight-medium);
      color: var(--ds-fg-muted);
      text-decoration: none;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
    }

    .ops-nav a:hover {
      color: var(--ds-fg);
      background: var(--ds-nav-bg-hover);
      text-decoration: none;
    }

    .ops-nav a.active {
      color: var(--ds-nav-active-fg);
      border-bottom-color: var(--ds-nav-active-border);
    }
  `,
})
export class OpsNavComponent {
  protected readonly items: readonly OpsNavItem[] = [
    { path: "/operations", labelKey: "ops.nav.dashboard", exact: true },
    { path: "/operations/timeline", labelKey: "ops.nav.timeline", exact: false },
    {
      path: "/operations/regressions",
      labelKey: "ops.nav.regressions",
      exact: false,
    },
    { path: "/operations/watches", labelKey: "ops.nav.watches", exact: false },
    {
      path: "/operations/remediation",
      labelKey: "ops.nav.remediation",
      exact: false,
    },
  ];
}
