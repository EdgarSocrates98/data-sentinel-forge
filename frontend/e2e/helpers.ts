import type { Page } from "@playwright/test";

/**
 * Shared E2E helpers — route inventory, preference seeding, axe runner.
 *
 * The app persists theme in localStorage `ds-theme` ("dark"|"light") and
 * locale in `ds-locale` ("pt-BR"|"en"); both are read before bootstrap,
 * so seeding via `page.addInitScript` is equivalent to a returning user.
 */

export type Theme = "dark" | "light";
export type Locale = "pt-BR" | "en";

export interface NavRoute {
  /** URL path served by the Angular router. */
  path: string;
  /** Expected localized page heading / document title (minus "— Data Sentinel"). */
  title: Record<Locale, string>;
}

/** The 8 primary navigation routes (matches the sidenav). */
export const NAV_ROUTES: NavRoute[] = [
  {
    path: "/",
    title: { "pt-BR": "Visão geral", en: "Overview" },
  },
  {
    path: "/investigations",
    title: { "pt-BR": "Investigações", en: "Investigations" },
  },
  {
    path: "/evidence-graph",
    title: { "pt-BR": "Grafo de evidências", en: "Evidence Graph" },
  },
  {
    path: "/workloads",
    title: { "pt-BR": "Workloads — Glue & EMR", en: "Workloads — Glue & EMR" },
  },
  {
    path: "/spark-plans",
    title: { "pt-BR": "Planos Spark", en: "Spark Plans" },
  },
  {
    path: "/quality-lineage",
    title: { "pt-BR": "Qualidade e linhagem", en: "Quality & Lineage" },
  },
  {
    path: "/agents",
    title: { "pt-BR": "Agentes", en: "Agents" },
  },
  {
    path: "/reports",
    title: { "pt-BR": "Relatórios", en: "Reports" },
  },
];

/** Seed theme + locale before the app bootstraps. */
export async function seedPrefs(
  page: Page,
  prefs: { theme: Theme; locale: Locale },
): Promise<void> {
  await page.addInitScript(
    ({ theme, locale }) => {
      try {
        window.localStorage.setItem("ds-theme", theme);
        window.localStorage.setItem("ds-locale", locale);
      } catch {
        /* storage unavailable — defaults apply */
      }
    },
    { theme: prefs.theme, locale: prefs.locale },
  );
}

/** Navigate and wait until the routed page heading is rendered. */
export async function gotoRoute(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "domcontentloaded" });
  await page.locator("#page-title").first().waitFor();
}
