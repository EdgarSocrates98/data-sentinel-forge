import { Injectable, inject } from "@angular/core";
import { Title } from "@angular/platform-browser";
import { RouterStateSnapshot, TitleStrategy } from "@angular/router";

import { I18nService } from "./i18n.service";

/**
 * Route `title` fields carry i18n keys; this strategy translates them
 * and keeps `<title>` in sync when the locale changes.
 */
@Injectable({ providedIn: "root" })
export class LocalizedTitleStrategy extends TitleStrategy {
  private readonly title = inject(Title);
  private readonly i18n = inject(I18nService);
  private lastSnapshot: RouterStateSnapshot | null = null;

  override updateTitle(snapshot: RouterStateSnapshot): void {
    this.lastSnapshot = snapshot;
    const key = this.buildTitle(snapshot);
    const app = this.i18n.t("app.name");
    this.title.setTitle(key ? `${this.i18n.t(key)} — ${app}` : app);
  }

  /** Re-apply the last title after a locale change. */
  refresh(): void {
    if (this.lastSnapshot) this.updateTitle(this.lastSnapshot);
  }
}
