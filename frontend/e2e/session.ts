import { spawn, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import path from "node:path";

import type { APIRequestContext, Page } from "@playwright/test";

/**
 * E2E session + fixture constants (ds-0102).
 *
 * The Playwright-spawned backend (see webServer env in
 * playwright.config.ts) is pinned to `DATA_SENTINEL_TOKEN` =
 * `E2E_SESSION_TOKEN` and `DATA_SENTINEL_DB` = `E2E_DB_PATH`, so specs
 * authenticate deterministically and never touch the developer's real
 * `~/.data-sentinel/sentinel.db` store.
 *
 * `E2E_SESSION_TOKEN` is a LOCAL TEST FIXTURE: it only ever reaches a
 * Playwright-spawned 127.0.0.1 server inside the same test run. It is
 * not a real credential — real deployments generate their own token
 * per boot (SessionAuth in src/data_sentinel/api/app.py).
 */

/** Bearer token pinned into the spawned backend via env. */
export const E2E_SESSION_TOKEN =
  process.env["DS_E2E_TOKEN"] ?? "ds-e2e-local-session-token";

/** API base URL compiled into the SPA (environments/*.ts). */
export const E2E_API_BASE = "http://127.0.0.1:8790/api/v1";

/** Repo root — the backend webServer cwd; fixture files live under it. */
export const REPO_ROOT = path.resolve(__dirname, "..", "..");

/**
 * SQLite file the spawned backend persists to — inside the gitignored
 * test-results dir so reruns accumulate state only under this suite
 * and the developer's real store is never touched.
 */
export const E2E_DB_PATH = path.resolve(
  __dirname,
  "..",
  "test-results",
  "ds-e2e.sqlite",
);

/* ------------------------------------------------------------------ */
/* Test data — repo fixtures (marked as such per spec; do not inline   */
/* fabricated payloads in specs).                                       */
/* ------------------------------------------------------------------ */

/** Absolute path to a repo fixture usable as an investigation input. */
export function fixtureFile(rel: string): string {
  return path.join(REPO_ROOT, "fixtures", rel);
}

/** Spark physical plan with a CartesianProduct — yields real findings. */
export const FIXTURE_SPARK_PLAN = fixtureFile("plans/cartesian.txt");

/** Glue-style driver log (OOM) — second input to keep SSE live longer. */
export const FIXTURE_GLUE_LOG = fixtureFile("logs/glue_oom.log");

/** Tool manifest names (GET /api/v1/tools) the new-investigation form offers. */
export const FIXTURE_TOOL_SPARK_PLAN = "sentinel.spark.analyze_plan";
export const FIXTURE_TOOL_CW_LOGS = "sentinel.cloudwatch.analyze_logs";

/* sessionStorage keys — mirror core/session/session.service.ts. */
const STORAGE_TOKEN_KEY = "ds-session-token";
const STORAGE_ESTABLISHED_KEY = "ds-session-established-at";

/**
 * Seed an already-established session before the app bootstraps
 * (equivalent to a returning tab). Used by specs that exercise feature
 * routes rather than the gate itself — the journey spec goes through
 * the REAL gate UI instead of this.
 */
export async function seedSession(page: Page): Promise<void> {
  await page.addInitScript(
    ({ token, tokenKey, establishedKey }) => {
      try {
        window.sessionStorage.setItem(tokenKey, token);
        window.sessionStorage.setItem(establishedKey, String(Date.now()));
      } catch {
        /* storage unavailable — defaults apply */
      }
    },
    {
      token: E2E_SESSION_TOKEN,
      tokenKey: STORAGE_TOKEN_KEY,
      establishedKey: STORAGE_ESTABLISHED_KEY,
    },
  );
}

/* ------------------------------------------------------------------ */
/* Backend restart-equivalent helper (ds-0102 journey).                 */
/*                                                                     */
/* A REAL restart of the Playwright-managed server on :8790 would      */
/* race concurrent specs under `fullyParallel` — a 2–3s bind gap is a  */
/* flaky ERR_CONNECTION_REFUSED for any sibling page load. Instead we  */
/* prove restart-persistence honestly: spawn a SECOND uvicorn process  */
/* over the SAME SQLite store and assert the investigation report is   */
/* still there. That is exactly what a restart relies on — state       */
/* durable beyond the process, not process memory.                     */
/* ------------------------------------------------------------------ */

/** Find an ephemeral localhost port. */
export async function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = createServer();
    srv.once("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const addr = srv.address();
      srv.close(() =>
        resolve(typeof addr === "object" && addr ? addr.port : 0),
      );
    });
  });
}

/** POSIX-style path safe to embed in a Python single-quoted literal. */
function posix(p: string): string {
  return p.split(path.sep).join("/");
}

/**
 * Spawn a fresh backend process against the SAME SQLite store as the
 * Playwright-managed server. Caller must invoke `stop()`.
 */
export async function startSecondServer(): Promise<{
  baseUrl: string;
  stop: () => Promise<void>;
}> {
  const port = await freePort();
  const venvPython = path.join(REPO_ROOT, ".venv", "bin", "python");
  const args = [
    "-c",
    "import uvicorn; from data_sentinel.api import create_app; " +
      `uvicorn.run(create_app(allowed_roots=['${posix(REPO_ROOT)}'], ` +
      `db_path='${posix(E2E_DB_PATH)}'), ` +
      `host='127.0.0.1', port=${port}, log_level='error')`,
  ];
  const proc: ChildProcess = spawn(venvPython, args, {
    cwd: REPO_ROOT,
    env: { ...process.env, DATA_SENTINEL_TOKEN: E2E_SESSION_TOKEN },
    stdio: ["ignore", "pipe", "pipe"],
  });
  const baseUrl = `http://127.0.0.1:${port}/api/v1`;
  const ready = await waitForHealth(baseUrl, 30_000, proc);
  if (!ready) {
    proc.kill("SIGKILL");
    throw new Error(`second backend did not become healthy on :${port}`);
  }
  return {
    baseUrl,
    stop: () =>
      new Promise<void>((resolve) => {
        proc.once("exit", () => resolve());
        proc.kill("SIGTERM");
        setTimeout(() => {
          proc.kill("SIGKILL");
          resolve();
        }, 5_000).unref();
      }),
  };
}

async function waitForHealth(
  baseUrl: string,
  timeoutMs: number,
  proc: ChildProcess,
): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (proc.exitCode !== null) return false;
    try {
      const res = await fetch(`${baseUrl}/health`);
      if (res.ok) return true;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  return false;
}

/* ------------------------------------------------------------------ */
/* Request ledger for the no-cloud / no-unexpected-mutation assertion.  */
/* ------------------------------------------------------------------ */

export interface RequestEntry {
  method: string;
  host: string;
  path: string;
  url: string;
}

/** Attach a request ledger to a page; inspect at the end of a journey. */
export function recordRequests(page: Page): RequestEntry[] {
  const log: RequestEntry[] = [];
  page.on("request", (req) => {
    const u = new URL(req.url());
    log.push({
      method: req.method(),
      host: u.host,
      path: u.pathname,
      url: req.url(),
    });
  });
  return log;
}

/**
 * POST bodies the journey deliberately triggers (validated by test
 * steps). Anything else mutating is a contract violation.
 */
const EXPECTED_POST_PATHS: RegExp[] = [
  /^\/api\/v1\/investigations$/,
  /^\/api\/v1\/watches$/,
  /^\/api\/v1\/watches\/[^/]+\/(run|pause|resume|delete)$/,
  /^\/api\/v1\/remediation\/plans$/,
  /^\/api\/v1\/remediation\/plans\/[^/]+\/(submit|approve|reject|dry-run|execute-local)$/,
];

/**
 * Assert every recorded request stayed on loopback hosts and every
 * mutation POST went to an endpoint the journey intentionally calls —
 * i.e. no cloud call, no hidden mutation (§1.5 / ds-0102).
 */
export function auditRequestLog(log: RequestEntry[]): string[] {
  const problems: string[] = [];
  for (const e of log) {
    if (!e.host.startsWith("127.0.0.1:") && !e.host.startsWith("localhost:")) {
      problems.push(`non-local request: ${e.method} ${e.url}`);
      continue;
    }
    if (e.method === "POST" || e.method === "PUT" || e.method === "PATCH" || e.method === "DELETE") {
      if (!e.host.startsWith("127.0.0.1:8790")) {
        problems.push(`mutation off the API server: ${e.method} ${e.url}`);
      } else if (!EXPECTED_POST_PATHS.some((re) => re.test(e.path))) {
        problems.push(`unexpected mutation: ${e.method} ${e.path}`);
      }
    }
  }
  return problems;
}

/** Authenticated GET helper against an explicit API base. */
export async function apiGet(
  request: APIRequestContext,
  baseUrl: string,
  path: string,
): Promise<{ status: number; body: unknown }> {
  const res = await request.get(`${baseUrl}${path}`, {
    headers: { Authorization: `Bearer ${E2E_SESSION_TOKEN}` },
  });
  return { status: res.status(), body: await res.json() };
}
