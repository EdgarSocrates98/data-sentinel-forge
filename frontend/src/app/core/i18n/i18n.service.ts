import { Injectable, signal } from "@angular/core";

import { EN, PT_BR, type TranslationDict } from "./translations";

export type Locale = "pt-BR" | "en";

const STORAGE_KEY = "ds-locale";

/**
 * Dependency-light translation service backed by a signal.
 * Default locale: pt-BR. Fallback chain: active locale → en → key.
 */
@Injectable({ providedIn: "root" })
export class I18nService {
  private readonly dicts: Record<Locale, TranslationDict> = {
    "pt-BR": PT_BR,
    en: EN,
  };

  private readonly _locale = signal<Locale>(initialLocale());
  readonly locale = this._locale.asReadonly();

  constructor() {
    this.applyDocumentLang(this._locale());
  }

  /** Translate a key in the active locale (en fallback). */
  t(key: string): string {
    const dict = this.dicts[this._locale()];
    return dict[key] ?? this.dicts.en[key] ?? key;
  }

  setLocale(locale: Locale): void {
    this._locale.set(locale);
    this.applyDocumentLang(locale);
    try {
      localStorage.setItem(STORAGE_KEY, locale);
    } catch {
      /* storage unavailable — non-fatal */
    }
  }

  toggleLocale(): void {
    this.setLocale(this._locale() === "pt-BR" ? "en" : "pt-BR");
  }

  private applyDocumentLang(locale: Locale): void {
    if (typeof document !== "undefined") {
      document.documentElement.lang = locale;
    }
  }
}

function initialLocale(): Locale {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "pt-BR" || stored === "en") return stored;
  } catch {
    /* storage unavailable */
  }
  return "pt-BR";
}
