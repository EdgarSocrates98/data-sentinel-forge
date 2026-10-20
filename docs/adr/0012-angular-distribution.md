# ADR-0012 — Angular Control Center Distribution

Status: Accepted (Cycle 08, ds-0097)

## Decision

Angular app ships as a **separate static build artifact**
(`frontend/dist/`), optionally served by the local API. It is NOT
bundled into the Python wheel.

## Rationale

- Keeps the wheel pure-Python and small; frontend requires Node to
  rebuild anyway.
- Local-first posture: `data-sentinel serve` can serve `frontend/dist`
  if present; otherwise the API works standalone.
- Independent release cadence for UI fixes.

## Consequences

- `pip install data-sentinel` never pulls Node assets.
- Users wanting the Control Center build the frontend or use a
  separately published dist artifact.
- No `portal start` integrated command this cycle (§4.4) — deferred
  until distribution path is exercised in a release.
