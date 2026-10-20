import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { NAV_ROUTES, gotoRoute, seedPrefs, type Locale, type Theme } from "./helpers";
import { seedSession } from "./session";

/**
 * axe-core accessibility sweep: every nav route × both themes × both
 * locales (WCAG 2.0/2.1 A+AA). Violations are attached to the report as
 * JSON so the HTML report carries the failing nodes verbatim.
 *
 * Routes are behind `authGuard` (ds-0101): a session is seeded before
 * boot so the scan covers the real feature pages, not the gate.
 */
const THEMES: Theme[] = ["dark", "light"];
const LOCALES: Locale[] = ["pt-BR", "en"];

test.beforeEach(async ({ page }) => {
  await seedSession(page);
});

for (const route of NAV_ROUTES) {
  for (const theme of THEMES) {
    for (const locale of LOCALES) {
      test(`axe ${route.path} [${theme}/${locale}]`, async ({ page }, testInfo) => {
        await seedPrefs(page, { theme, locale });
        await gotoRoute(page, route.path);

        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
          .analyze();

        if (results.violations.length > 0) {
          await testInfo.attach("axe-violations.json", {
            body: JSON.stringify(results.violations, null, 2),
            contentType: "application/json",
          });
        }
        const summary = results.violations.map(
          (v) =>
            `${v.id} (${v.impact}): ${v.nodes.length} node(s) — ${v.help}`,
        );
        expect(summary, `axe violations on ${route.path}`).toEqual([]);
      });
    }
  }
}
