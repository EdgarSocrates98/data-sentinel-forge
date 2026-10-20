import { ChangeDetectionStrategy, Component } from "@angular/core";

import { PageShellComponent } from "../../shared/page-shell/page-shell.component";

/**
 * AgentsComponent — real route for a studio shipping in a later phase
 * (ds-0072: minimal real routes, never simulated functionality).
 */
@Component({
  selector: "ds-agents",
  standalone: true,
  imports: [PageShellComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ds-page-shell
      titleKey="pages.agents.title"
      leadKey="pages.agents.lead"
      [plannedKeys]="planned"
    />
  `,
})
export class AgentsComponent {
  protected readonly planned: readonly string[] = [
    "pages.agents.planned.0",
    "pages.agents.planned.1",
    "pages.agents.planned.2",
  ];
}
