import { TestBed } from "@angular/core/testing";

import { I18nService } from "./i18n.service";

describe("I18nService", () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({});
  });

  it("defaults to pt-BR", () => {
    const i18n = TestBed.inject(I18nService);
    expect(i18n.locale()).toBe("pt-BR");
    expect(i18n.t("nav.investigations")).toBe("Investigações");
  });

  it("switches to en and back", () => {
    const i18n = TestBed.inject(I18nService);
    i18n.setLocale("en");
    expect(i18n.t("nav.investigations")).toBe("Investigations");
    i18n.setLocale("pt-BR");
    expect(i18n.t("nav.investigations")).toBe("Investigações");
  });

  it("falls back to the key when untranslated", () => {
    const i18n = TestBed.inject(I18nService);
    expect(i18n.t("missing.key")).toBe("missing.key");
  });
});
