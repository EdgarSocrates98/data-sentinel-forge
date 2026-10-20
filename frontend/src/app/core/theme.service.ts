import { Injectable, signal } from "@angular/core";

export type Theme = "dark" | "light";

const STORAGE_KEY = "ds-theme";

/**
 * Theme controller. Dark is the platform default; light is activated
 * via `data-theme="light"` on <html> and persisted in localStorage.
 */
@Injectable({ providedIn: "root" })
export class ThemeService {
  private readonly _theme = signal<Theme>(initialTheme());
  readonly theme = this._theme.asReadonly();

  constructor() {
    this.apply(this._theme());
  }

  toggle(): void {
    this.set(this._theme() === "dark" ? "light" : "dark");
  }

  set(theme: Theme): void {
    this._theme.set(theme);
    this.apply(theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* storage unavailable — non-fatal */
    }
  }

  private apply(theme: Theme): void {
    if (typeof document !== "undefined") {
      document.documentElement.dataset["theme"] = theme;
    }
  }
}

function initialTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    /* storage unavailable */
  }
  return "dark"; // spec: dark mode is the default visual identity
}
