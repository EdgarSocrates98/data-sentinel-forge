/**
 * Normalization of `POST /api/v1/analyze/{id}` payloads.
 *
 * The endpoint delegates to different tool implementations, so the
 * wire shape varies: diagnostics-backed tools emit
 * `{report_id, findings, summary, limitations}`, the EMR analyzers emit
 * `{analyzer, findings, limitations}` and in-process tools emit their
 * own payloads. Everything is read defensively — absent fields stay
 * absent and unknown shapes degrade to "no findings" rather than
 * fabricated rows.
 */

/** A finding as normalized from any analyzer payload. */
export interface NormalizedFinding {
  id: string;
  severity: string;
  status: string;
  category: string;
  explanation: string;
  evidenceIds: string[];
  recommendations: string[];
  validationSteps: string[];
  alternatives: string[];
}

/** A normalized analyze result for display. */
export interface AnalysisResult {
  /** Human label (usually the tool id) for this run. */
  label: string;
  /** File path that was analyzed. */
  file: string;
  /** Report-level summary line, when the tool emits one. */
  summary: string | null;
  findings: NormalizedFinding[];
  limitations: string[];
  /** Scalar top-level fields (report_id, analyzer, events, kind…). */
  extras: Array<[string, string]>;
}

const SKIP_KEYS = new Set(["findings", "limitations", "summary"]);

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v): v is string => typeof v === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

/** Defensive extraction of a `findings[]` array from a raw payload. */
export function extractFindings(payload: unknown): NormalizedFinding[] {
  if (!isRecord(payload) || !Array.isArray(payload["findings"])) return [];
  return (payload["findings"] as unknown[])
    .filter(isRecord)
    .map((f, i) => ({
      id: asString(f["finding_id"]) || `finding-${i}`,
      severity: asString(f["severity"]) || "INFO",
      status: asString(f["status"]) || "UNKNOWN",
      category: asString(f["category"]),
      explanation: asString(f["explanation"]),
      evidenceIds: asStringList(f["evidence_ids"]),
      recommendations: asStringList(f["recommendations"]),
      validationSteps: asStringList(f["validation_steps"]),
      alternatives: asStringList(f["alternatives"]),
    }));
}

/** Defensive extraction of a `limitations[]` array. */
export function extractLimitations(payload: unknown): string[] {
  if (!isRecord(payload)) return [];
  return asStringList(payload["limitations"]);
}

/** Scalar top-level fields rendered verbatim (no interpretation). */
function extractExtras(payload: unknown): Array<[string, string]> {
  if (!isRecord(payload)) return [];
  const out: Array<[string, string]> = [];
  for (const [k, v] of Object.entries(payload)) {
    if (SKIP_KEYS.has(k)) continue;
    if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
      out.push([k, String(v)]);
    }
  }
  return out.sort(([a], [b]) => a.localeCompare(b));
}

/** Normalize a raw analyze response into a display-ready result. */
export function normalizeAnalysisResult(
  label: string,
  file: string,
  payload: Record<string, unknown>,
): AnalysisResult {
  return {
    label,
    file,
    summary: isRecord(payload) && typeof payload["summary"] === "string"
      ? payload["summary"]
      : null,
    findings: extractFindings(payload),
    limitations: extractLimitations(payload),
    extras: extractExtras(payload),
  };
}

/** Count findings by an attribute (severity/status), sorted by key. */
export function countBy(
  findings: NormalizedFinding[],
  attr: "severity" | "status",
): Array<[string, number]> {
  const counts = new Map<string, number>();
  for (const f of findings) {
    const key = (attr === "severity" ? f.severity : f.status).toUpperCase();
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()].sort(([a], [b]) => a.localeCompare(b));
}
