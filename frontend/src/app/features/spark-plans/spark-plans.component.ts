import { ChangeDetectionStrategy, Component } from "@angular/core";

import { PageShellComponent } from "../../shared/page-shell/page-shell.component";

/**
 * SparkPlansComponent — real route for a studio shipping in a later phase
 * (ds-0072: minimal real routes, never simulated functionality).
 */
@Component({
  selector: "ds-spark-plans",
  standalone: true,
  imports: [PageShellComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ds-page-shell
      titleKey="pages.sparkPlans.title"
      leadKey="pages.sparkPlans.lead"
      [plannedKeys]="planned"
    />
  `,
})
export class SparkPlansComponent {
  protected readonly planned: readonly string[] = [
    "pages.sparkPlans.planned.0",
    "pages.sparkPlans.planned.1",
    "pages.sparkPlans.planned.2",
  ];
}
