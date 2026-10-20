import { ChangeDetectionStrategy, Component } from "@angular/core";

import { PageShellComponent } from "../../shared/page-shell/page-shell.component";

/**
 * EvidenceGraphComponent — real route for a studio shipping in a later phase
 * (ds-0072: minimal real routes, never simulated functionality).
 */
@Component({
  selector: "ds-evidence-graph",
  standalone: true,
  imports: [PageShellComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ds-page-shell
      titleKey="pages.evidenceGraph.title"
      leadKey="pages.evidenceGraph.lead"
      [plannedKeys]="planned"
    />
  `,
})
export class EvidenceGraphComponent {
  protected readonly planned: readonly string[] = [
    "pages.evidenceGraph.planned.0",
    "pages.evidenceGraph.planned.1",
    "pages.evidenceGraph.planned.2",
    "pages.evidenceGraph.planned.3",
    "pages.evidenceGraph.planned.4",
  ];
}
