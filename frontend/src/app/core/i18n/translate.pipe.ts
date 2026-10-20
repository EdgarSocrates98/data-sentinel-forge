import { Pipe, type PipeTransform, inject } from "@angular/core";

import { I18nService } from "./i18n.service";

/**
 * `{{ 'nav.dashboard' | t }}` — impure so signal-driven locale
 * changes re-render labels under OnPush change detection.
 */
@Pipe({ name: "t", standalone: true, pure: false })
export class TranslatePipe implements PipeTransform {
  private readonly i18n = inject(I18nService);

  transform(key: string): string {
    return this.i18n.t(key);
  }
}
