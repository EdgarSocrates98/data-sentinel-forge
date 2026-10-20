# Frontend Security Upgrade — Cycle 07 (items 1.3 + 1.6)

Date: 2026-10-20. Environment: Node v22.23.2, npm 10.9.8, Linux.

## 1. Dependency audit and upgrade (§1.3)

### Before (Angular 19.2.25)

`npm audit` reported **40 vulnerable packages**: 2 critical, 26 high,
10 moderate, 2 low.

- **Angular runtime** (`@angular/*` @ 19.2.25): hydration DOM-clobbering,
  i18n XSS via event-handler attributes, `formatDate` DoS,
  `HttpTransferCache` weak cache-key / cross-request reuse, SSR matrix-param
  DoS, host-binding sanitization bypass. All advisories covered
  `<= 19.2.25` — i.e. **the entire 19.x line is affected; no 19.x patch exists**.
- **Build toolchain**: `piscina <4.9.4` (critical, RCE gadget), `tar`
  (critical, arbitrary file overwrite), `vite <=6.4.2`, `esbuild <0.28.1`,
  `postcss <=8.5.22`, `serialize-javascript`, `webpack-dev-server <=5.2.5`,
  `http-proxy-middleware`, `node-forge`, `selfsigned`, `sigstore` chain, etc.
- **Test toolchain**: `karma` tree → `braces <=3.0.3` stack-exhaustion DoS.

### Decision: Angular 20.3.34 / CLI 20.3.40 (not 21/22)

- `npx ng update @angular/core@20 @angular/cli@20` (migrations ran clean).
- Chose the **newest 20.x stable**, per the cycle directive
  "prefer the newest Angular 19.x/20.x that resolves cleanly":
  - 19.x cannot fix the runtime advisories (all ranges are `<=19.2.25`).
  - 20.3.x satisfies Node `^20.19 || ^22.12 || >=24` (we run 22.23.2) and
    pulls fixed toolchain deps (`@angular/build` → vite 7.3.6,
    esbuild 0.28.1, piscina 5.2.0, postcss 8.5.23).
  - npm's `audit fix --force` would jump to Angular 21/22 — two/three major
    versions of churn for build-deps only; not justified in a hardening cycle.
- TypeScript `~5.7.3 → ~5.9.3` (peer dep of `@angular/compiler-cli@20` is
  `>=5.8 <6.0`).

### Targeted `overrides` (package.json)

| Package | Pinned | Why |
|---|---|---|
| `webpack-dev-middleware` | `7.4.6` | build-angular@20.3.40 pins 7.4.2; advisory `<7.4.5` (path traversal). Patch-level bump. |
| `uuid` | `11.1.1` | `sockjs` requires `^8`; advisory `<11.1.1` (v3/v5/v6 `buf` bounds). sockjs only calls `uuid().v4` and is only reachable via the legacy webpack dev-server — `ng serve` on the `application` builder uses Vite. |

### After

**12 high vulnerabilities remain — zero critical, zero moderate,
zero low, and zero in Angular runtime packages or the production bundle.**
All 12 trace to a single unpatched root:

- `braces@3.0.3` — stack-exhaustion DoS via deeply nested glob patterns.
  **3.0.3 is the latest published release**; there is no fix to take.
  It reaches us through `chokidar@3.6.0` (karma, webpack-dev-server) and
  `micromatch` (fast-glob, http-proxy-middleware). The other 11 audit
  entries (`karma`, `karma-jasmine`, `karma-jasmine-html-reporter`,
  `chokidar`, `micromatch`, `fast-glob`, `http-proxy-middleware`,
  `webpack-dev-server`, `@angular-devkit/build-angular`,
  `@angular-devkit/build-webpack`, `@angular/build`) are
  "depends on vulnerable versions" chains of the same root.

Honest risk assessment: exploitability requires feeding a hostile glob
pattern to a dev-time tool — all affected packages are devDependencies on
developer machines / CI, not shipped to users. karma is EOL upstream;
the durable fix is migrating `ng test` to vitest/web-test-runner — out of
scope here because the suite must keep running under
`npx ng test --browsers=ChromeHeadless`.

### Verification

- `npm install` clean (no peer conflicts).
- `npx ng build` — production bundle OK.
- `npx ng test --watch=false --browsers=ChromeHeadless` — **49/49 SUCCESS**.

## 2. Reproducible browser tests (§1.6)

Playwright E2E lives in `frontend/e2e/` with `frontend/playwright.config.ts`.

- **Servers**: config spawns both — `uv run data-sentinel serve --port 8790`
  (cwd = repo root, `webServer.cwd`) and `npx ng serve --port 4200`
  (port fixed by backend CORS allowlist). `reuseExistingServer` outside CI.
- **Projects**: `chromium`, `firefox`, `webkit` (all three defined).
- **Specs**: `navigation.spec.ts` — backend health, boot, all 8 nav routes
  (URL + localized `#page-title` + `<title>` + active nav state), sidenav
  click-through, 404 redirect, theme toggle persistence, locale toggle,
  seeded-en smoke. `a11y.spec.ts` — `@axe-core/playwright` WCAG 2.0/2.1
  A+AA scan on every route × {dark, light} × {pt-BR, en} (32 scans/browser).
- Browsers installed to `~/.cache/ms-playwright` (outside the repo);
  `test-results/`, `playwright-report/`, `blob-report/` gitignored.
- Run: `npm run e2e` (install once with `npm run e2e:install`).

### Real results — 2026-10-20

| Browser | Result |
|---|---|
| Chromium 156.0.8078.4 | **47/47 passed** (46 + health smoke) |
| Firefox 157.0 | **47/47** (46 passed + 1 skipped: the health smoke is chromium-only because the API rate-limits localhost at 120 req/min) |
| WebKit 27.2 | **BLOCKED — did not run.** Binary downloaded, but the host lacks `libavif16`; `playwright install-deps` requires sudo, unavailable in this environment. The project stays defined for CI/dev machines that have it. |

Note: the API requires a bearer session token the SPA doesn't yet send,
so data endpoints answer 401/429 and pages render their error states;
navigation, theme, i18n, and axe assertions are unaffected (verified —
this is real observed behavior, not mocked).

### axe findings and fixes applied

| Violation | Where | Fix |
|---|---|---|
| `label-content-name-mismatch` (serious) | locale toggle button, all pages — visible "EN"/"PT" not in aria-label | `app.component.html`: accessible name now starts with the visible text (`EN — Switch to English` / `PT — Mudar para português`) |
| `aria-valid-attr-value` (critical) | `/quality-lineage` tabs — `aria-controls` pointed at `panel-*` ids absent in loading/error states | `quality-lineage.component.html`: `aria-controls` emitted only when the panel exists (`toolsState() === 'ok'`) |
| `aria-valid-attr-value` (latent, same pattern) | expand buttons in `quality-lineage` (`obs-*`) and `investigation-detail` (`fd-*`) — targets only exist when expanded | same conditional `aria-controls` fix (proactive; these pages aren't in the scanned route set with data) |
| **App bug found by E2E**: `<title>` stayed pt-BR after locale toggle | `LocalizedTitleStrategy` registered via `useClass` created a second instance; the component's refresh `effect` held the other instance with `lastSnapshot === null` | `app.config.ts`: `useClass` → `useExisting` so the Router and `AppComponent` share one instance. Verified live: title toggles `Visão geral ↔ Overview — Data Sentinel` |

Final state: **0 axe violations** across 64 scans (8 routes × 2 themes ×
2 locales × 2 browsers).

## 3. Residual risks

- `braces` DoS — unfixed upstream; dev-only; revisit when a patch exists
  or when migrating off karma.
- karma ecosystem is EOL — plan a vitest-based runner migration (also
  removes the braces/chokidar chain entirely).
- WebKit coverage gap until `libavif16` lands on the host
  (`sudo npx playwright install-deps`).
- Angular 20.x is supported until ~Nov 2026; 21/22 is the next planned
  jump and already clears the remaining build-dep advisories.
- Backend bearer token has no SPA affordance yet — E2E covers shell and
  error states; authenticated data flows remain unit-test-covered only.
