import { ChangeDetectionStrategy, Component } from "@angular/core";

import { PageShellComponent } from "../../shared/page-shell/page-shell.component";

/**
 * InvestigationsComponent — real route for a studio shipping in a later phase
 * (ds-0072: minimal real routes, never simulated functionality).
 */
@Component({
  selector: "ds-investigations",
  standalone: true,
  imports: [PageShellComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ds-page-shell
      titleKey="pages.investigations.title"
      leadKey="pages.investigations.lead"
      [plannedKeys]="planned"
    />
  `,
})
export class InvestigationsComponent {
  protected readonly planned: readonly string[] = [
    "pages.investigations.planned.0",
    "pages.investigations.planned.1",
    "pages.investigations.planned.2",
    "pages.investigations.planned.3",
    "pages.investigations.planned.4",
    "pages.investigations.planned.5",
  ];
}
