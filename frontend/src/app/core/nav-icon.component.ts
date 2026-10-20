import { ChangeDetectionStrategy, Component, input } from "@angular/core";

/**
 * Inline SVG icons for the primary nav. Decorative only
 * (`aria-hidden`); the adjacent text label carries meaning.
 */
@Component({
  selector: "ds-nav-icon",
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.8"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      @switch (name()) {
        @case ("overview") {
          <rect x="3" y="3" width="7" height="9" rx="1" />
          <rect x="14" y="3" width="7" height="5" rx="1" />
          <rect x="14" y="12" width="7" height="9" rx="1" />
          <rect x="3" y="16" width="7" height="5" rx="1" />
        }
        @case ("investigation") {
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.35-4.35" />
        }
        @case ("graph") {
          <circle cx="5" cy="6" r="3" />
          <circle cx="19" cy="6" r="3" />
          <circle cx="12" cy="18" r="3" />
          <path d="m7.5 8 3 7M16.5 8l-3 7M8 6h8" />
        }
        @case ("workload") {
          <rect x="2" y="7" width="20" height="14" rx="2" />
          <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
        }
        @case ("spark") {
          <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z" />
        }
        @case ("lineage") {
          <path d="M6 3v12" />
          <circle cx="6" cy="18" r="3" />
          <circle cx="18" cy="6" r="3" />
          <path d="M18 9a9 9 0 0 1-9 9" />
        }
        @case ("agent") {
          <rect x="4" y="8" width="16" height="12" rx="2" />
          <path d="M12 8V4M8 4h8" />
          <circle cx="9" cy="14" r="1" fill="currentColor" />
          <circle cx="15" cy="14" r="1" fill="currentColor" />
        }
        @case ("report") {
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <path d="M14 2v6h6M9 13h6M9 17h6" />
        }
        @case ("operations") {
          <path d="M3 12h4l3-8 4 16 3-8h4" />
        }
        @default {
          <circle cx="12" cy="12" r="9" />
        }
      }
    </svg>
  `,
  styles: `
    :host {
      display: inline-flex;
      flex: 0 0 auto;
    }
  `,
})
export class NavIconComponent {
  readonly name = input.required<string>();
}
