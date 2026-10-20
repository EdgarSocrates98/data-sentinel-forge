import { expect, test } from "@playwright/test";

import { NAV_ROUTES, gotoRoute, seedPrefs } from "./helpers";
import { seedSession } from "./session";

/**
 * Boot + navigation smoke tests against a real backend
 * (`uv run data-sentinel serve --port 8790`, spawned by playwright.config).
 *
 * Every feature route sits behind `authGuard` (ds-0101), so each test
 * seeds an established session in sessionStorage (the spawned backend
 * accepts `E2E_SESSION_TOKEN` — see e2e/session.ts). These specs still
 * assert shell/routing/i18n/theme behavior rather than data payloads.
 */

const API_HEALTH = "http://127.0.0.1:8790/api/v1/health";

test.beforeEach(async ({ page }) => {
  await seedSession(page);
});

test("real backend is up and healthy", async ({ request }, testInfo) => {
  // One browser project only: the API rate-limits 127.0.0.1 at 120 req/min
  // and this assertion is identical per project.
  test.skip(
    testInfo.project.name !== "chromium",
    "single-project smoke check",
  );
  // The shared rate bucket can transiently return 429 under the
  // parallel a11y/navigation wave — retry within a short window rather
  // than flake on a contract that is intentionally throttled.
  let res;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    res = await request.get(API_HEALTH);
    if (res.status() !== 429) break;
    await new Promise((r) => setTimeout(r, 1500));
  }
  expect(res!.status()).toBe(200);
  const body = await res!.json();
  expect(body.status).toBe("ok");
  expect(body.api).toBe("v1");
});

test("app boots on ng serve", async ({ page }) => {
  const failures: string[] = [];
  page.on("pageerror", (err) => failures.push(String(err)));
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveTitle(/Data Sentinel/);
  await expect(page.locator(".sidenav")).toBeVisible();
  await expect(page.locator("#page-title")).toBeVisible();
  expect(failures, "uncaught page errors").toEqual([]);
});

for (const route of NAV_ROUTES) {
  test(`route ${route.path} renders (pt-BR default)`, async ({ page }) => {
    await gotoRoute(page, route.path);
    await expect(page).toHaveURL(
      route.path === "/" ? /\/$/ : new RegExp(`${route.path}$`),
    );
    await expect(page.locator("#page-title")).toHaveText(
      route.title["pt-BR"],
    );
    await expect(page).toHaveTitle(`${route.title["pt-BR"]} — Data Sentinel`);
    // Sidenav marks the active route.
    const active = page.locator(".sidenav a.active");
    await expect(active).toHaveCount(1);
    await expect(active).toHaveAttribute(
      "href",
      route.path === "/" ? "/" : route.path,
    );
  });
}

test("navigates all routes through the sidenav", async ({ page }) => {
  await gotoRoute(page, "/");
  for (const route of NAV_ROUTES.slice(1)) {
    await page.locator(`.sidenav a[href="${route.path}"]`).click();
    await expect(page).toHaveURL(new RegExp(`${route.path}$`));
    await expect(page.locator("#page-title")).toHaveText(
      route.title["pt-BR"],
    );
  }
});

test("unknown route redirects to dashboard", async ({ page }) => {
  await gotoRoute(page, "/does-not-exist");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator("#page-title")).toHaveText("Visão geral");
});

test("theme toggle flips data-theme and persists", async ({ page }) => {
  await gotoRoute(page, "/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Alternar para tema claro" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  expect(await page.evaluate(() => localStorage.getItem("ds-theme"))).toBe(
    "light",
  );
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("locale toggle flips lang and translates chrome", async ({ page }) => {
  await gotoRoute(page, "/");
  await expect(page.locator("html")).toHaveAttribute("lang", "pt-BR");
  await page.getByRole("button", { name: "Switch to English" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator("#page-title")).toHaveText("Overview");
  await expect(page).toHaveTitle("Overview — Data Sentinel");
  await expect(page.locator(".sidenav a").first()).toContainText("Overview");
});

test("seeded en locale renders English chrome end-to-end", async ({
  page,
}) => {
  await seedPrefs(page, { theme: "dark", locale: "en" });
  await gotoRoute(page, "/evidence-graph");
  await expect(page).toHaveTitle("Evidence Graph — Data Sentinel");
  await expect(page.locator("#page-title")).toHaveText("Evidence Graph");
});
