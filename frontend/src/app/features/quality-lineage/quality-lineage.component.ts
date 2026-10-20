import { ChangeDetectionStrategy, Component } from "@angular/core";

import { PageShellComponent } from "../../shared/page-shell/page-shell.component";

/**
 * QualityLineageComponent — real route for a studio shipping in a later phase
 * (ds-0072: minimal real routes, never simulated functionality).
 */
@Component({
  selector: "ds-quality-lineage",
  standalone: true,
  imports: [PageShellComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ds-page-shell
      titleKey="pages.qualityLineage.title"
      leadKey="pages.qualityLineage.lead"
      [plannedKeys]="planned"
    />
  `,
})
export class QualityLineageComponent {
  protected readonly planned: readonly string[] = [
    "pages.qualityLineage.planned.0",
    "pages.qualityLineage.planned.1",
    "pages.qualityLineage.planned.2",
  ];
}
