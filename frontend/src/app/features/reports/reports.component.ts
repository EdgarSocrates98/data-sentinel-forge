import { ChangeDetectionStrategy, Component } from "@angular/core";

import { PageShellComponent } from "../../shared/page-shell/page-shell.component";

/**
 * ReportsComponent — real route for a studio shipping in a later phase
 * (ds-0072: minimal real routes, never simulated functionality).
 */
@Component({
  selector: "ds-reports",
  standalone: true,
  imports: [PageShellComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ds-page-shell
      titleKey="pages.reports.title"
      leadKey="pages.reports.lead"
      [plannedKeys]="planned"
    />
  `,
})
export class ReportsComponent {
  protected readonly planned: readonly string[] = [
    "pages.reports.planned.0",
    "pages.reports.planned.1",
    "pages.reports.planned.2",
  ];
}
