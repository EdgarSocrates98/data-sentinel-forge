import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

/**
 * Reproducible browser E2E (Cycle 07 §1.6).
 *
 * Two web servers are spawned automatically:
 *  - backend:  `uv run data-sentinel serve --port 8790` from the repo root
 *              (requires the `uv` env; API binds 127.0.0.1 and requires a
 *              bearer token for mutating/authed endpoints — /health is open).
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
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
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
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: `npx ng serve --port ${FRONTEND_PORT}`,
      url: BASE_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
});
