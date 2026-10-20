import { expect, test } from "@playwright/test";

import { gotoRoute } from "./helpers";
import {
  E2E_API_BASE,
  E2E_SESSION_TOKEN,
  FIXTURE_GLUE_LOG,
  FIXTURE_SPARK_PLAN,
  FIXTURE_TOOL_CW_LOGS,
  FIXTURE_TOOL_SPARK_PLAN,
  apiGet,
  auditRequestLog,
  recordRequests,
  startSecondServer,
} from "./session";

/**
 * Authenticated end-to-end journey (ds-0102) against the real spawned
 * backend — no mocks: the session is established through the actual
 * gate UI and every subsequent screen reads from the FastAPI process.
 *
 * Test data comes from repo fixtures (see e2e/session.ts):
 *   - fixtures/plans/cartesian.txt  → sentinel.spark.analyze_plan
 *   - fixtures/logs/glue_oom.log    → sentinel.cloudwatch.analyze_logs
 * Both are allowlisted file types under the repo-root allowed root.
 */

const PROBLEM_TEXT =
  "Job falhando: plano Spark contém CartesianProduct e o driver " +
  "estourou memória — investigar.";

/**
 * Rate-bucket spacing for the LOCAL full-suite run: the API throttles
 * 120 req/min per client IP on a sliding 60s window and each journey
 * emits ~40 calls, so serialized journeys must also be spaced — the
 * previous browser's tail otherwise still counts against the next.
 * In CI each matrix job owns a private backend (own bucket), so the
 * stagger is skipped.
 */
const AUTH_STAGGER_MS: Record<string, number> = {
  "firefox-auth": 30_000,
  "webkit-auth": 60_000,
};

test.beforeAll(async ({}, testInfo) => {
  const delay = process.env["CI"]
    ? 0
    : (AUTH_STAGGER_MS[testInfo.project.name] ?? 0);
  if (delay > 0) {
    // Raise the hook's own timeout past the stagger.
    test.setTimeout(delay + 60_000);
    await new Promise((r) => setTimeout(r, delay));
  }
});

test("gate rejects an invalid token before accepting the real one", async ({
  page,
}) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  // authGuard redirects unauthenticated users to the gate.
  await expect(page).toHaveURL(/\/session\?/);
  await expect(page.locator("#gate-title")).toHaveText(
    "Conectar ao Sentinel",
  );

  // Invalid token: establish() probes GET /capabilities → 401 → "invalid".
  await page.locator("#session-token").fill("ds-e2e-not-the-token");
  await page.getByRole("button", { name: "Conectar" }).click();
  await expect(page.locator(".field-error")).toContainText("Token inválido");
  await expect(page).toHaveURL(/\/session/);

  // Real token (the value pinned into the spawned backend via env).
  await page.locator("#session-token").fill(E2E_SESSION_TOKEN);
  await page.getByRole("button", { name: "Conectar" }).click();
  await expect(page).toHaveURL(/127\.0\.0\.1:4200\/?$/);
  await expect(page.locator("#page-title")).toHaveText("Visão geral");
});

test("authenticated journey: session → investigation → ops surfaces", async ({
  page,
  request,
}) => {
  test.setTimeout(120_000);
  const requestLog = recordRequests(page);
  let investigationId = "";
  let findingsCount = 0;

  await test.step("session gate → dashboard with real capabilities", async () => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/session\?/);
    await page.locator("#session-token").fill(E2E_SESSION_TOKEN);
    await page.getByRole("button", { name: "Conectar" }).click();
    await expect(page).toHaveURL(/127\.0\.0\.1:4200\/?$/);
    await expect(page.locator("#page-title")).toHaveText("Visão geral");

    // Capabilities card — counts come from GET /capabilities, /tools,
    // /agents against the real API.
    const counts = page.locator(".counts .count");
    await expect(counts).toHaveCount(3);
    for (const locator of await counts.all()) {
      expect(Number(await locator.innerText())).toBeGreaterThan(0);
    }
  });

  await test.step("agents registry loads real data", async () => {
    await gotoRoute(page, "/agents");
    await expect(page.locator("#page-title")).toHaveText("Agentes");
    await expect(
      page.locator('section[aria-labelledby="registry-title"] tbody tr')
        .first(),
    ).toBeVisible();
  });

  await test.step("create investigation from repo fixtures", async () => {
    await gotoRoute(page, "/investigations/new");
    await expect(page.locator("#page-title")).toHaveText("Nova investigação");

    await page.locator("#problem").fill(PROBLEM_TEXT);

    // Fixture row 1: spark physical plan (fixtures/plans/cartesian.txt).
    await page.getByRole("button", { name: "Adicionar artefato" }).click();
    await page.locator("#tool-0").selectOption(FIXTURE_TOOL_SPARK_PLAN);
    await page.locator("#path-0").fill(FIXTURE_SPARK_PLAN);

    // Fixture row 2: glue-style OOM log (fixtures/logs/glue_oom.log).
    await page.getByRole("button", { name: "Adicionar artefato" }).click();
    await page.locator("#tool-1").selectOption(FIXTURE_TOOL_CW_LOGS);
    await page.locator("#path-1").fill(FIXTURE_GLUE_LOG);

    await page
      .getByRole("button", { name: "Iniciar investigação" })
      .click();
    await expect(page).toHaveURL(/\/investigations\/inv-[0-9a-f]+/);
    investigationId = page.url().split("/").pop() ?? "";
    expect(investigationId).toMatch(/^inv-[0-9a-f]+$/);
  });

  await test.step("SSE events arrive (UI + wire-level contract)", async () => {
    // The detail page either catches the live stream (running state →
    // .events list) or lands on the already-finished report — both are
    // correct real behavior depending on timing.
    const events = page.locator(".events li");
    const findingsTitle = page.locator("#findings-title");
    await expect(events.first().or(findingsTitle)).toBeVisible();

    // Deterministic SSE check: the stream endpoint replays stored
    // events for the same investigation over authenticated HTTP.
    const sse = await request.get(
      `${E2E_API_BASE}/investigations/${investigationId}/stream`,
      { headers: { Authorization: `Bearer ${E2E_SESSION_TOKEN}` } },
    );
    expect(sse.ok()).toBeTruthy();
    expect(sse.headers()["content-type"]).toContain("text/event-stream");
    const body = await sse.text();
    expect(body).toContain("event: INVESTIGATION_STARTED");
    expect(body).toContain("event: TOOL_COMPLETED");
    expect(body).toContain("event: INVESTIGATION_COMPLETED");
    expect(body).toContain(FIXTURE_TOOL_SPARK_PLAN);
  });

  await test.step("findings render with real severity/status data", async () => {
    await expect(page.locator("#findings-title")).toBeVisible({
      timeout: 20_000,
    });
    const rows = page.locator(
      'section[aria-labelledby="findings-title"] tbody tr:not(.detail-row)',
    );
    findingsCount = await rows.count();
    // The two fixtures deterministically produce ≥3 findings
    // (CartesianProduct HIGH sql_antipattern + scan/oom companions).
    expect(findingsCount).toBeGreaterThanOrEqual(3);
    await expect(
      page.locator('section[aria-labelledby="findings-title"]'),
    ).toContainText("CartesianProduct");

    // Expand the first finding — detail row carries evidence ids.
    await page
      .getByRole("button", { name: "Expandir" })
      .first()
      .click();
    await expect(page.locator(".detail-row")).toBeVisible();
    await expect(page.locator(".detail-row")).toHaveAttribute(
      "id",
      /^fd-/,
    );
  });

  await test.step("evidence inspector lists real evidence", async () => {
    await expect(page.locator("#ev-title")).toBeVisible();
    const items = page.locator(".ev-item");
    expect(await items.count()).toBeGreaterThanOrEqual(2);
    await items.first().locator("summary").click();
    await expect(items.first().locator(".kv")).toBeVisible();
  });

  await test.step("evidence graph renders nodes/edges from the report", async () => {
    await page.getByRole("link", { name: "Ver no grafo" }).click();
    await expect(page).toHaveURL(
      new RegExp(`/evidence-graph\\?investigation=${investigationId}`),
    );
    await expect(page.locator("#graph-title")).toBeVisible();
    // investigation + ≥3 findings + evidence nodes at minimum.
    const nodeRows = page.locator(
      'section[aria-labelledby="a11y-title"] table >> nth=0 >> tbody tr',
    );
    expect(await nodeRows.count()).toBeGreaterThanOrEqual(4);
  });

  await test.step("reports surface lists the investigation", async () => {
    await gotoRoute(page, "/reports");
    await expect(page.locator("#page-title")).toHaveText("Relatórios");
    await expect(
      page.locator(
        'section[aria-labelledby="reports-list-title"] tbody tr code',
        { hasText: investigationId },
      ),
    ).toBeVisible();
  });

  await test.step("reload keeps the session (sessionStorage)", async () => {
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/reports$/);
    await expect(page.locator("#page-title")).toHaveText("Relatórios");
    // Sanity: the token really is in sessionStorage, not a cookie/URL.
    const stored = await page.evaluate(() =>
      sessionStorage.getItem("ds-session-token"),
    );
    expect(stored).toBe(E2E_SESSION_TOKEN);
  });

  await test.step("a fresh tab is unauthenticated (storage isolation)", async () => {
    const tab = await page.context().newPage();
    try {
      await tab.goto("/reports", { waitUntil: "domcontentloaded" });
      await expect(tab).toHaveURL(/\/session/);
      await expect(tab.locator("#gate-title")).toBeVisible();
    } finally {
      await tab.close();
    }
  });

  await test.step("backend restart → investigation persists in the store", async () => {
    // A REAL kill+rebind of the shared :8790 server would race sibling
    // specs under fullyParallel; instead a second uvicorn process opens
    // the SAME SQLite store — restart-equivalent proof that state is
    // durable beyond process memory (see e2e/session.ts).
    const second = await startSecondServer();
    try {
      const res = await apiGet(
        request,
        second.baseUrl,
        `/investigations/${investigationId}`,
      );
      expect(res.status).toBe(200);
      const body = res.body as {
        status?: string;
        findings?: unknown[];
        evidence?: unknown[];
      };
      expect(body.status).toBe("completed");
      expect(body.findings?.length ?? 0).toBe(findingsCount);
      expect(body.evidence?.length ?? 0).toBeGreaterThanOrEqual(2);
    } finally {
      await second.stop();
    }
  });

  await test.step("quality/lineage route renders", async () => {
    await gotoRoute(page, "/quality-lineage");
    await expect(page.locator("#page-title")).toHaveText(
      "Qualidade e linhagem",
    );
    await expect(page.locator("#quality-title")).toBeVisible();
  });

  await test.step("watch is created DISABLED; manual eval only", async () => {
    // Run-unique id: the e2e SQLite store persists across runs and the
    // API returns 409 on duplicate watch_id.
    const watchId = `e2e-watch-${Date.now().toString(36)}`;
    await gotoRoute(page, "/operations/watches");
    await expect(page.locator("#page-title")).toHaveText(
      "Central de watches",
    );
    // The page declares watches never auto-start (§8.5 note).
    await expect(page.locator(".note-line")).toContainText(
      "nascem desabilitados",
    );

    await page.locator("#watch-id").fill(watchId);
    await page.locator("#watch-workload").fill("e2e-fixture-job");
    await page.locator("#watch-platform").fill("spark");
    await page.locator("#watch-rule").selectOption("regression");
    await page.locator("#watch-metrics").fill("duration_s");
    await page
      .getByRole("button", { name: "Criar watch" })
      .click();
    await expect(page.locator(".ok-note")).toContainText(watchId);

    const row = page.locator("tbody tr", { hasText: watchId });
    await expect(row).toBeVisible();
    // Created disabled — the API never enables monitoring on create.
    await expect(row).toContainText("desabilitado");
    await expect(row.locator(".ds-badge--status-running")).toHaveCount(0);

    // Explicit manual evaluation — no snapshots for this job → no alerts.
    await row.getByRole("button", { name: "Avaliar agora" }).click();
    await expect(
      page.locator("tr.run-row", { hasText: "alerta" }),
    ).toBeVisible();

    // Two-step delete keeps the shared e2e store tidy.
    await row.getByRole("button", { name: "Excluir" }).click();
    await page
      .getByRole("button", { name: "Confirmar exclusão" })
      .click();
    await expect(
      page.locator("tbody tr", { hasText: watchId }),
    ).toHaveCount(0);
  });

  await test.step("remediation plan lifecycle: DRAFT → approval → dry-run → local exec", async () => {
    await gotoRoute(page, "/operations/remediation");
    await expect(page.locator("#page-title")).toHaveText(
      "Workspace de remediação",
    );
    // No-cloud posture is declared on the page.
    await expect(page.locator(".note-line")).toContainText("cloud");

    // Create a plan from a real finding of our investigation.
    await expect(
      page.locator(`#rem-inv option[value="${investigationId}"]`),
    ).toHaveCount(1);
    await page.locator("#rem-inv").selectOption(investigationId);

    const findingSelect = page.locator("#rem-finding");
    await expect(findingSelect).toBeEnabled();
    const findingOptions = page.locator("#rem-finding option:not([value=''])");
    await expect(findingOptions.first()).toBeAttached();
    const findingId = await findingOptions.first().getAttribute("value");
    await findingSelect.selectOption(findingId);

    await page
      .locator("#rem-title")
      .fill("E2E — remediar finding da investigação fixture");
    await page.getByRole("button", { name: "Criar plano" }).click();
    await expect(page.locator(".ok-note")).toContainText("DRAFT");
    await page
      .locator(".ok-note")
      .getByRole("button", { name: "Abrir" })
      .click();

    await expect(page.locator("#rem-detail-title")).toBeVisible();
    await expect(
      page.locator(".ds-badge", { hasText: "Rascunho" }).first(),
    ).toBeVisible();

    await page
      .getByRole("button", { name: "Submeter para aprovação" })
      .click();
    await expect(
      page.locator(".ds-badge", { hasText: "Aguardando aprovação" }).first(),
    ).toBeVisible({ timeout: 15_000 });

    await page.locator("#rem-approver").fill("e2e-operador");
    await page.getByRole("button", { name: "Aprovar" }).click();
    await expect(
      page.locator(".ds-badge", { hasText: "Aprovado" }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // Structured preview — asserts nothing is applied.
    await page.getByRole("button", { name: "Dry-run" }).click();
    await expect(page.locator("#rem-dryrun-title")).toBeVisible();
    await expect(page.locator("#rem-dryrun-title + p")).toContainText(
      "dry-run",
    );

    // Local execution: findings carry no allowlisted local_action, so
    // every change resolves to SKIPPED and the API reports no cloud call.
    await page
      .getByRole("button", { name: "Executar ações locais" })
      .click();
    await expect(page.locator("#rem-exec-title")).toBeVisible();
    await expect(
      page.locator(".ds-badge", { hasText: "SKIPPED" }).first(),
    ).toBeVisible();
    await expect(page.locator("#rem-exec-title ~ p")).toContainText(
      "nenhuma chamada cloud",
    );
  });

  await test.step("no cloud / unexpected mutation was issued", async () => {
    // Every request stayed on loopback; every POST hit an endpoint the
    // journey deliberately used — no hidden mutations, no egress.
    expect(auditRequestLog(requestLog)).toEqual([]);
    const posts = requestLog.filter((e) => e.method === "POST");
    const paths = posts.map((e) => e.path);
    expect(paths.some((p) => p === "/api/v1/investigations")).toBeTruthy();
    expect(paths.some((p) => p === "/api/v1/watches")).toBeTruthy();
    expect(
      paths.some((p) => /^\/api\/v1\/watches\/[^/]+\/run$/.test(p)),
    ).toBeTruthy();
    expect(paths.some((p) => p === "/api/v1/remediation/plans")).toBeTruthy();
    expect(
      paths.some((p) => p.endsWith("/execute-local")),
    ).toBeTruthy();
    // And the inverse: nothing hit the forbidden create-with-aws path
    // or rotated/revoked the session.
    expect(paths.some((p) => p.includes("/auth/rotate"))).toBeFalsy();
    expect(paths.some((p) => p.includes("/auth/revoke"))).toBeFalsy();
  });
});
