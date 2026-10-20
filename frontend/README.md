# Data Sentinel — Control Center (frontend)

Angular 19 frontend for the Sentinel Control Center. Standalone
components, signals, OnPush change detection, TypeScript strict mode,
lazy-loaded routes. No Angular Material, no NgRx — the design system
is custom (see "Design tokens" below).

## Commands

```bash
npm install        # install dependencies
npx ng serve       # dev server on http://localhost:4200
npx ng build       # production build → dist/frontend
npx ng test        # unit tests (Karma + Jasmine, ChromeHeadless)
```

The app expects the Control Center API at `http://127.0.0.1:8790`
(configured in `src/environments/`). Start the backend first — the
Overview page shows the real connection status; nothing is simulated.

## Structure

```
src/
  styles/tokens.css       3-layer design tokens (see below)
  styles.css              global base styles, a11y (skip link, focus, reduced-motion)
  environments/           apiBaseUrl per build configuration
  app/
    app.component.*       shell: topbar + sidenav + content + error toast
    app.routes.ts         lazy routes (/ , investigations, evidence-graph,
                          workloads, spark-plans, quality-lineage, agents, reports)
    core/
      api.models.ts       typed payloads mirroring FastAPI /api/v1 responses
      api.service.ts      typed API client (health, capabilities, tools,
                          agents, investigations, analyze, severities)
      api-error.store.ts  last-API-error signal store (toast)
      http-error.interceptor.ts  normalizes HttpErrorResponse → ApiError
      theme.service.ts    dark (default) / light theme, persisted
      i18n/               typed translation service (pt-BR default, en)
    shared/page-shell/    real placeholder page for upcoming studios
    features/             one component per route
```

## Design tokens

`src/styles/tokens.css` implements a strict 3-layer system:

1. **Primitive** (`--ds-p-*`) — raw palette, spacing scale, typography,
   radius, elevation, motion. Theme-agnostic; components never consume
   these directly.
2. **Semantic** (`--ds-bg`, `--ds-fg`, `--ds-accent`, `--ds-severity-*`,
   `--ds-confidence-*`, `--ds-success|warning|error|info`, …) — intent
   tokens. Dark theme is the default on `:root`;
   `[data-theme="light"]` re-declares this layer. Severity colors are
   deliberately distinct from confidence/support colors.
3. **Component** (`--ds-topbar-bg`, `--ds-nav-active-fg`,
   `--ds-card-bg`, `--ds-btn-*`, `--ds-badge-*`, `--ds-chart-*`, …) —
   per-surface tokens that components consume.

Toggle themes with `ThemeService` (topbar button persists to
`localStorage`).

## i18n

`I18nService` (signal-based, dependency-free): pt-BR default, en
fallback. Use `{{ 'key' | t }}` in templates. Route titles are i18n
keys resolved by `LocalizedTitleStrategy`.

## Accessibility

Skip link, ARIA landmarks/labels, `:focus-visible` ring,
`prefers-reduced-motion` honored globally, dark/light themes target
WCAG 2.2 AA contrast, icons are decorative (`aria-hidden`) with text
labels.
