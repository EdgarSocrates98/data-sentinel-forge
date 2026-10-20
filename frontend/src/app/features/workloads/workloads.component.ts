import { ChangeDetectionStrategy, Component } from "@angular/core";

import { PageShellComponent } from "../../shared/page-shell/page-shell.component";

/**
 * WorkloadsComponent — real route for a studio shipping in a later phase
 * (ds-0072: minimal real routes, never simulated functionality).
 */
@Component({
  selector: "ds-workloads",
  standalone: true,
  imports: [PageShellComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ds-page-shell
      titleKey="pages.workloads.title"
      leadKey="pages.workloads.lead"
      [plannedKeys]="planned"
    />
  `,
})
export class WorkloadsComponent {
  protected readonly planned: readonly string[] = [
    "pages.workloads.planned.0",
    "pages.workloads.planned.1",
    "pages.workloads.planned.2",
  ];
}
