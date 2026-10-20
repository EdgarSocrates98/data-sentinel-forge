/**
 * Pure mapping helpers from API enum values to design-token badge
 * modifier classes (`ds-badge--*`, defined in styles.css). Keep them
 * total: any unknown value degrades to the neutral badge — never throw.
 */

const SEVERITIES = new Set(["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]);

/** Finding/severity value → `severity-<x>` modifier. */
export function severityClass(severity: string): string {
  const s = severity.toUpperCase();
  return `severity-${SEVERITIES.has(s) ? s : "INFO"}`;
}

/**
 * Confidence-like values (Evidence.confidence is numeric 0-1; Hypothesis
 * and Finding carry CONFIRMED|PROBABLE|POSSIBLE|UNKNOWN labels) →
 * `confidence-<x>` modifier.
 */
export function confidenceClass(value: string | number): string {
  if (typeof value === "number") {
    if (value >= 0.8) return "confidence-HIGH";
    if (value >= 0.5) return "confidence-MEDIUM";
    if (value > 0) return "confidence-LOW";
    return "confidence-UNKNOWN";
  }
  switch (value.toUpperCase()) {
    case "HIGH":
    case "CONFIRMED":
      return "confidence-HIGH";
    case "MEDIUM":
    case "PROBABLE":
      return "confidence-MEDIUM";
    case "LOW":
    case "POSSIBLE":
      return "confidence-LOW";
    default:
      return "confidence-UNKNOWN";
  }
}

/** Quality observation verdict → `status-<x>` modifier. */
export function observationStatusClass(status: string): string {
  switch (status.toUpperCase()) {
    case "PASS":
      return "status-ok";
    case "FAIL":
      return "status-error";
    case "WARN":
      return "status-warn";
    default:
      return "status-neutral";
  }
}

/** Investigation/hypothesis lifecycle → `status-<x>` modifier. */
export function statusClass(status: string): string {
  switch (status.toLowerCase()) {
    case "running":
      return "status-running";
    case "completed":
    case "supported":
      return "status-ok";
    case "failed":
    case "refuted":
      return "status-error";
    default:
      return "status-neutral";
  }
}
