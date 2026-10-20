#!/usr/bin/env node
/**
 * Initial-bundle size gate (ds-0102).
 *
 * Sums the JS + CSS files the production `index.html` actually loads
 * on first paint (the "initial" bundle in Angular budget terms) and
 * fails when the raw byte total exceeds the threshold. Lazy chunks are
 * intentionally not counted — they ship on demand.
 *
 * The angular.json production budget enforces the same ceiling at
 * build time; this script is the explicit CI-visible check.
 */
import { readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const LIMIT_KB = 600;
const browserDir = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",
  "dist",
  "frontend",
  "browser",
);

const html = readFileSync(join(browserDir, "index.html"), "utf8");
const assets = [
  ...new Set(
    [
      ...html.matchAll(
        /<script[^>]+src="([^"]+\.js)"|<link[^>]+href="([^"]+\.css)"/g,
      ),
    ]
      .map((m) => (m[1] ?? m[2]).replace(/^\//, ""))
      .filter((f) => !f.startsWith("http")),
  ),
];

if (assets.length === 0) {
  console.error(`no initial assets found in ${browserDir}/index.html`);
  process.exit(1);
}

let total = 0;
for (const f of assets) {
  const bytes = statSync(join(browserDir, f)).size;
  total += bytes;
  console.log(`  ${(bytes / 1024).toFixed(1).padStart(8)} kB  ${f}`);
}
const kb = total / 1024;
console.log(`initial bundle: ${kb.toFixed(1)} kB (limit ${LIMIT_KB} kB)`);
if (kb > LIMIT_KB) {
  console.error(`FAIL: initial bundle exceeds ${LIMIT_KB} kB raw`);
  process.exit(1);
}
