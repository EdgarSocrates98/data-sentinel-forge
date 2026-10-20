import type { ToolManifestEntry } from "../core/api.models";

/**
 * Helpers over the MCP-style tool manifest (GET /api/v1/tools).
 * The analyze endpoint (`POST /api/v1/analyze/{id}`) only forwards a
 * single `{file}` argument, so a tool is callable through it iff every
 * required input is exactly `file`. Tools like detect_drift (2 files),
 * lineage.impact (file+target) or emr.estimate_cost (non-file inputs)
 * are detectable via `missingInputs` and must be declared unavailable
 * honestly — never hidden behind a fake form.
 */

/** Required input names declared by a manifest inputSchema. */
export function requiredInputs(tool: ToolManifestEntry): string[] {
  const schema = tool.inputSchema;
  const required = Array.isArray(schema["required"])
    ? (schema["required"] as unknown[])
    : [];
  return required.filter((r): r is string => typeof r === "string");
}

/** Property names declared by a manifest inputSchema. */
export function schemaProperties(tool: ToolManifestEntry): string[] {
  const schema = tool.inputSchema;
  const properties =
    schema["properties"] && typeof schema["properties"] === "object"
      ? (schema["properties"] as Record<string, unknown>)
      : {};
  return Object.keys(properties);
}

/** A manifest entry is file-compatible when `file` covers its inputs. */
export function acceptsSingleFile(tool: ToolManifestEntry): boolean {
  const required = requiredInputs(tool);
  const properties = schemaProperties(tool);
  return required.every((r) => r === "file") && properties.includes("file");
}

/**
 * Inputs the tool needs beyond what `POST /analyze/{id}` can supply —
 * empty for file-compatible tools. Used to explain honestly why a tool
 * cannot run through this API.
 */
export function missingInputs(tool: ToolManifestEntry): string[] {
  return acceptsSingleFile(tool)
    ? []
    : requiredInputs(tool).filter((r) => r !== "file");
}

/** `sentinel.spark.analyze_plan` → `spark.analyze_plan` (analyze path). */
export function analyzerSuffix(toolName: string): string {
  return toolName.startsWith("sentinel.")
    ? toolName.slice("sentinel.".length)
    : toolName;
}

/**
 * Extract a human-readable detail string from either a normalized
 * `ApiError` (produced by httpErrorInterceptor) or a raw
 * `HttpErrorResponse` (interceptor not in the pipeline, e.g. tests).
 */
export function apiErrorDetail(err: unknown): string | null {
  if (!err || typeof err !== "object") return null;
  const e = err as Record<string, unknown>;
  if (typeof e["detail"] === "string") return e["detail"];
  const body = e["error"];
  if (body && typeof body === "object") {
    const d = (body as Record<string, unknown>)["detail"];
    if (typeof d === "string") return d;
  }
  return null;
}
