import type {
  DatasetRef,
  LineageIngestResult,
  QualityAssessResult,
  QualityObservation,
} from "../../core/api.models";

/**
 * Defensive parsers for the per-tool payloads returned by
 * `POST /api/v1/analyze/{id}` (quality.assess, lineage.ingest). The
 * wire is `dict[str, Any]` — every field is guarded so malformed or
 * partial payloads degrade to empty collections, never to fake rows.
 */

function isRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function asString(v: unknown): string {
  return typeof v === "string" ? v : "";
}

function asStringList(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string");
}

function parseDatasetRef(v: unknown): DatasetRef | null {
  if (!isRecord(v)) return null;
  return {
    namespace: asString(v["namespace"]),
    name: asString(v["name"]),
    platform: asString(v["platform"]),
    catalog: asString(v["catalog"]),
    account: asString(v["account"]),
    region: asString(v["region"]),
    version: asString(v["version"]),
    identifier: asString(v["identifier"]),
  };
}

function parseObservation(v: unknown, index: number): QualityObservation | null {
  if (!isRecord(v)) return null;
  return {
    observation_id: asString(v["observation_id"]) || `obs-${index}`,
    rule_id: asString(v["rule_id"]),
    dataset: parseDatasetRef(v["dataset"]),
    run_id: asString(v["run_id"]),
    timestamp: typeof v["timestamp"] === "string" ? v["timestamp"] : null,
    observed_value: v["observed_value"],
    expected_value: v["expected_value"],
    status: asString(v["status"]) || "UNKNOWN",
    source: asString(v["source"]),
    metric_name: asString(v["metric_name"]),
    unit: asString(v["unit"]),
    provenance: asString(v["provenance"]),
    limitations: asStringList(v["limitations"]),
  };
}

/** Parse the `sentinel.quality.assess` payload. */
export function parseQualityResult(payload: unknown): QualityAssessResult {
  const observations = isRecord(payload) && Array.isArray(payload["observations"])
    ? payload["observations"]
        .map((o, i) => parseObservation(o, i))
        .filter((o): o is QualityObservation => o !== null)
    : [];
  const count =
    isRecord(payload) && typeof payload["count"] === "number"
      ? payload["count"]
      : observations.length;
  return { observations, count };
}

/** Parse the `sentinel.lineage.ingest` payload. */
export function parseLineageResult(payload: unknown): LineageIngestResult {
  if (!isRecord(payload)) {
    return { events: 0, kind: "", downstream: {}, limitations: [] };
  }
  const downstream: Record<string, string[]> = {};
  const rawDown = payload["downstream"];
  if (isRecord(rawDown)) {
    for (const [k, v] of Object.entries(rawDown)) {
      downstream[k] = asStringList(v);
    }
  }
  return {
    events: typeof payload["events"] === "number" ? payload["events"] : 0,
    kind: asString(payload["kind"]),
    downstream,
    limitations: asStringList(payload["limitations"]),
  };
}

/** One directed dataset→dataset edge. */
export interface LineageEdge {
  from: string;
  to: string;
}

/** Sorted edge list derived from the `downstream` adjacency map. */
export function lineageEdges(downstream: Record<string, string[]>): LineageEdge[] {
  const edges: LineageEdge[] = [];
  for (const [from, tos] of Object.entries(downstream)) {
    for (const to of tos) edges.push({ from, to });
  }
  return edges.sort(
    (a, b) => a.from.localeCompare(b.from) || a.to.localeCompare(b.to),
  );
}

/** Sorted unique dataset keys appearing as source or target. */
export function lineageNodes(downstream: Record<string, string[]>): string[] {
  const nodes = new Set<string>();
  for (const [from, tos] of Object.entries(downstream)) {
    nodes.add(from);
    for (const to of tos) nodes.add(to);
  }
  return [...nodes].sort();
}

/** `DatasetRef` → `namespace/name` display label. */
export function datasetLabel(d: DatasetRef | null): string {
  if (!d) return "—";
  return d.namespace ? `${d.namespace}/${d.name}` : d.name || "—";
}

/** Render an observed/expected scalar compactly. */
export function scalarLabel(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}
