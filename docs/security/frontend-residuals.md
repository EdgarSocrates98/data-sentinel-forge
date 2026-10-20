# Frontend residual advisories (ds-0102)

Snapshot of `npm audit` for `frontend/` — **14 advisories (2 moderate,
12 high), all confined to the development toolchain**. Re-check at every
dependency bump or monthly, whichever comes first.

## Headline classification

| Question | Answer |
| --- | --- |
| Reachable from the shipped production bundle? | **No.** `npm audit --omit=dev` reports **0 vulnerabilities**. Everything below sits under `devDependencies`; the served app is compiled output (`main-*.js`), none of these packages execute at runtime in the browser. |
| Reachable from CI/dev workstations? | Yes — `ng serve`/`ng build`/`ng test`/`ng e2e` load these packages locally. Exploitability still requires an attacker-controlled input reaching a dev process (crafted glob pattern, malicious editor string, hostile MCP/HTTP endpoint, or code execution already achieved to influence `vitest` mock redirects). |
| Existing overrides | `webpack-dev-middleware@7.4.6`, `uuid@11.1.1`, `tinypool@2.2.0` in `package.json#overrides` — they pin past earlier advisories and stay in place. |
| Why not `npm audit fix --force`? | Every fix offered is a SemVer-major jump (`@angular/cli@22`, `vitest@5`, `@angular-devkit/build-angular` downgrade to `20.0.6` is itself flagged as major churn). Forcing would desynchronize the Angular 20.3.x toolchain ahead of upstream support — documented trade-off, not neglect. |

## Advisory-by-advisory

| Advisory (package) | Severity | In lockfile via | Exploitability in our usage | Shipped-bundle reachable? |
| --- | --- | --- | --- | --- |
| `@modelcontextprotocol/sdk` — experimental tasks not tied to session; cross-origin redirect re-send of headers/body; request-size memory exhaustion; bearer tokens accepted for another service | high + moderate | `@angular/cli@20.3.40` (transitive) | Only relevant when running the Angular MCP server (`ng mcp`), which we do not expose; the CLI is invoked locally by developers/CI. | No — dev-only |
| `@vitest/mocker` — path traversal / arbitrary file read via redirect mock | moderate | `vitest@3.2.7` → `@angular/build` | Requires a victim to run `vitest` against attacker-influenced config/mock registry; our tests are repo-controlled. | No — test runner only |
| `braces` — stack-exhaustion DoS via deeply nested patterns (≤3.0.3) | high | `chokidar` → `webpack-dev-server`; `micromatch` → `fast-glob`, `http-proxy-middleware` | Needs an attacker to feed a pathological glob to the dev watcher/proxy — inputs are our own file tree and build config. | No — dev server only |
| `vite` — `launch-editor` Windows argument-escaping / flag-misinterpretation / `existsSync` bypass (7.0.0–7.3.6) | high + moderate | `@angular/build` | Triggered only when the dev server opens an editor from an error overlay with a hostile `EDITOR`/URL — Windows-specific and interactive. | No — dev server only |
| `vitest` — same mocker redirect advisory (direct devDep) | moderate | direct devDependency | Same as `@vitest/mocker` above. | No — test runner only |
| `chokidar`, `micromatch`, `fast-glob`, `http-proxy-middleware`, `webpack-dev-server` | high | transitive of `@angular-devkit/build-angular`/`build-webpack` | All carry the `braces`/`micromatch` chain — same dev-server glob/proxy exposure as above. | No — dev server only |
| `@angular-devkit/build-angular`, `@angular/build`, `@angular-devkit/build-webpack`, `@angular/cli` | high | direct devDependencies | Flagged solely through the transitive chains above; no distinct vulnerability of their own. | No — build tooling only |

## Policy

- CI (`frontend` workflow) runs `npm audit --omit=dev` as an **enforced**
  gate — a new *production-reachable* advisory fails the build.
- The full `npm audit` report is emitted and archived as a CI artifact
  for tracking, without failing on this known dev-toolchain residual.
- Re-evaluate forced upgrades when Angular publishes a supported path
  that clears the `vite`/`vitest`/`braces` chains (or upstream backports
  fixes to the 20.3.x line).

## Related

- `frontend/SECURITY-UPGRADE.md` — Cycle 07 security cycle: the Angular
  19 → 20.3.x move cleared the runtime advisories then present; the
  remaining set above is the documented residual.
- `.github/workflows/frontend.yml` — audit + bundle-size enforcement.
