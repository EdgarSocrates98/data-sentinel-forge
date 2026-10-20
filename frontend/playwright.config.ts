import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

import { E2E_DB_PATH, E2E_SESSION_TOKEN } from "./e2e/session";

/**
 * Reproducible browser E2E (Cycle 07 §1.6, Cycle 08.1 ds-0102).
 *
 * Two web servers are spawned automatically:
 *  - backend:  `uv run data-sentinel serve --port 8790` from the repo root
 *              (requires the `uv` env; API binds 127.0.0.1 and requires a
 *              bearer token for mutating/authed endpoints — /health is open).
 *              `DATA_SENTINEL_TOKEN` pins the session token so specs can
 *              authenticate deterministically (a local-test-only value —
 *              never a real secret) and `DATA_SENTINEL_DB` redirects
 *              persistence to a gitignored test-results SQLite file so
 *              developer state is untouched.
 *  - frontend: `npx ng serve --port 4200` (port fixed by backend CORS allowlist).
 *
 * Browsers live outside the repo in the default Playwright cache
 * (`~/.cache/ms-playwright`). Install with:
 *     npx playwright install chromium firefox webkit
 * (`--with-deps` needs sudo; WebKit additionally needs the system
 *  `libavif16` package on this host — see SECURITY-UPGRADE.md.)
 */
const FRONTEND_PORT = 4200;
const API_PORT = 8790;
const BASE_URL = `http://127.0.0.1:${FRONTEND_PORT}`;
const REPO_ROOT = path.resolve(__dirname, "..");

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  fullyParallel: true,
  forbidOnly: !!process.env["CI"],
  retries: process.env["CI"] ? 2 : 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `uv run data-sentinel serve --port ${API_PORT}`,
      cwd: REPO_ROOT,
      url: `http://127.0.0.1:${API_PORT}/api/v1/health`,
      env: {
        // Local-test-only credentials/state — deterministic E2E (ds-0102).
        DATA_SENTINEL_TOKEN: E2E_SESSION_TOKEN,
        DATA_SENTINEL_DB: E2E_DB_PATH,
      },
      reuseExistingServer: !process.env["CI"],
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: `npx ng serve --port ${FRONTEND_PORT}`,
      url: BASE_URL,
      reuseExistingServer: !process.env["CI"],
      timeout: 180_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
  projects: [
    /*
     * Rate-limit-aware split (ds-0102): the backend token-buckets
     * 120 req/min per client IP and every spec shares 127.0.0.1.
     * authenticated.spec.ts cannot absorb a stray 429 (the gate's
     * /capabilities probe would read as "invalid token"), so locally
     * the journey runs FIRST — serialized across browsers via project
     * dependencies — while the bucket is quiet. The remaining specs
     * tolerate transient 429s (their routes render localized error
     * panels whose titles, landmarks and markup still satisfy the
     * assertions), so they fan out in parallel only after all
     * journeys finish.
     *
     * In CI the dependency chains are intentionally dropped: every
     * matrix job is a separate runner with its own spawned backend —
     * its own rate bucket — so a job needs only the browser named by
     * its project. The webkit job splits auth/rest into two steps for
     * the same quiet-window effect.
     */
    {
      name: "chromium-auth",
      testMatch: /authenticated\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox-auth",
      testMatch: /authenticated\.spec\.ts/,
      use: { ...devices["Desktop Firefox"] },
      dependencies: process.env["CI"] ? [] : ["chromium-auth"],
    },
    {
      name: "webkit-auth",
      testMatch: /authenticated\.spec\.ts/,
      use: { ...devices["Desktop Safari"] },
      dependencies: process.env["CI"] ? [] : ["firefox-auth"],
    },
    {
      name: "chromium",
      testIgnore: /authenticated\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
      dependencies: process.env["CI"] ? [] : ["webkit-auth"],
    },
    {
      name: "firefox",
      testIgnore: /authenticated\.spec\.ts/,
      use: { ...devices["Desktop Firefox"] },
      dependencies: process.env["CI"] ? [] : ["webkit-auth"],
    },
    {
      name: "webkit",
      testIgnore: /authenticated\.spec\.ts/,
      use: { ...devices["Desktop Safari"] },
      dependencies: process.env["CI"] ? [] : ["webkit-auth"],
    },
  ],
});
