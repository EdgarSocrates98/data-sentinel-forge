import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
} from "@angular/core";
import { RouterLink, RouterLinkActive, RouterOutlet } from "@angular/router";

import { ApiErrorStore } from "./core/api-error.store";
import { I18nService } from "./core/i18n/i18n.service";
import { LocalizedTitleStrategy } from "./core/i18n/localized-title.strategy";
import { TranslatePipe } from "./core/i18n/translate.pipe";
import { ThemeService } from "./core/theme.service";
import { NavIconComponent } from "./core/nav-icon.component";

interface NavItem {
  path: string;
  labelKey: string;
  icon: string;
  exact: boolean;
}

@Component({
  selector: "app-root",
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    TranslatePipe,
    NavIconComponent,
  ],
  templateUrl: "./app.component.html",
  styleUrl: "./app.component.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent {
  protected readonly i18n = inject(I18nService);
  protected readonly themeService = inject(ThemeService);
  protected readonly errorStore = inject(ApiErrorStore);
  private readonly titleStrategy = inject(LocalizedTitleStrategy);

  protected readonly navItems: readonly NavItem[] = [
    { path: "/", labelKey: "nav.dashboard", icon: "overview", exact: true },
    {
      path: "/investigations",
      labelKey: "nav.investigations",
      icon: "investigation",
      exact: false,
    },
    {
      path: "/evidence-graph",
      labelKey: "nav.evidenceGraph",
      icon: "graph",
      exact: false,
    },
    {
      path: "/workloads",
      labelKey: "nav.workloads",
      icon: "workload",
      exact: false,
    },
    {
      path: "/spark-plans",
      labelKey: "nav.sparkPlans",
      icon: "spark",
      exact: false,
    },
    {
      path: "/quality-lineage",
      labelKey: "nav.qualityLineage",
      icon: "lineage",
      exact: false,
    },
    { path: "/agents", labelKey: "nav.agents", icon: "agent", exact: false },
    { path: "/reports", labelKey: "nav.reports", icon: "report", exact: false },
    {
      path: "/operations",
      labelKey: "nav.operations",
      icon: "operations",
      exact: false,
    },
  ];

  constructor() {
    // Keep <title> in sync when the locale changes.
    effect(() => {
      this.i18n.locale();
      this.titleStrategy.refresh();
    });
  }

  protected toggleLocale(): void {
    this.i18n.toggleLocale();
  }

  protected toggleTheme(): void {
    this.themeService.toggle();
  }

  protected dismissError(): void {
    this.errorStore.dismiss();
  }
}
