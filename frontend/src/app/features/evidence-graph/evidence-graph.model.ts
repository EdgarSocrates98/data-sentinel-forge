/**
 * Evidence-graph model (ds-0074). Pure, deterministic functions that
 * derive a node/edge graph from a real `InvestigationReport` — the API
 * does not expose a dedicated graph endpoint, so relations are rebuilt
 * from the report's own evidence/hypothesis references, mirroring the
 * backend `diagnostics/incident.py` vocabulary (SUPPORTED_BY,
 * ASSOCIATED_WITH, PRODUCED...). Nothing is simulated: when the report
 * references evidence it does not carry, the gap is declared in
 * `limitations` and the node is flagged `referencedOnly`.
 */

import type {
  Evidence,
  Finding,
  Hypothesis,
  InvestigationReport,
} from "../../core/api.models";

export type GraphNodeKind =
  | "investigation"
  | "finding"
  | "evidence"
  | "hypothesis"
  | "tool"
  | "agent";

export interface GraphNode {
  id: string;
  kind: GraphNodeKind;
  label: string;
  /**
   * Token-level class suffix used for coloring (e.g. `severity-HIGH`
   * for findings, `status-*`/`neutral` elsewhere).
   */
  accent: string;
  /** The real API payload this node renders — never fabricated. */
  data: Finding | Evidence | Hypothesis | InvestigationReport | string;
  /**
   * True when the node stands for an evidence_id the report references
   * but does not include as a full Evidence payload.
   */
  referencedOnly: boolean;
}

export interface GraphEdge {
  id: string;
  src: string;
  dst: string;
  /** Relation label, aligned with diagnostics/incident.py EdgeKind. */
  kind:
    | "PRODUCED"
    | "SUPPORTED_BY"
    | "ASSOCIATED_WITH"
    | "VALIDATED_BY"
    | "REFERENCED";
  /** The shared key that legitimizes the link (never empty). */
  justification: string;
}

export interface GraphModel {
  nodes: GraphNode[];
  edges: GraphEdge[];
  limitations: string[];
}

export interface PositionedNode extends GraphNode {
  x: number;
  y: number;
  w: number;
  h: number;
  layer: number;
}

export interface GraphLayout {
  nodes: PositionedNode[];
  edges: GraphEdge[];
  width: number;
  height: number;
}

const NODE_W = 232;
const NODE_H = 64;
const LANE_GAP = 120;
const ROW_GAP = 28;
const MARGIN = 32;

/**
 * Build the evidence graph for one investigation report.
 *
 * Relations (all justified by real payload fields):
 * - investigation --PRODUCED--> finding          (report.findings)
 * - investigation --ASSOCIATED_WITH--> tool      (report.tools_used)
 * - investigation --ASSOCIATED_WITH--> agent     (report.agents_used)
 * - evidence --SUPPORTED_BY--> finding           (finding.evidence_ids)
 * - evidence --SUPPORTED_BY--> hypothesis        (hypothesis.supporting_evidence)
 * - finding --ASSOCIATED_WITH--> hypothesis      (shared RCA category or
 *    shared evidence ids — how RootCauseEngine clusters)
 */
export function buildInvestigationGraph(
  report: InvestigationReport,
): GraphModel {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const limitations: string[] = [];
  const byId = new Map<string, GraphNode>();
  const edgeKeys = new Set<string>();

  const addNode = (node: GraphNode): GraphNode => {
    const existing = byId.get(node.id);
    if (existing) return existing;
    byId.set(node.id, node);
    nodes.push(node);
    return node;
  };

  const addEdge = (
    src: string,
    dst: string,
    kind: GraphEdge["kind"],
    justification: string,
  ): void => {
    if (!justification) {
      limitations.push(`edge dropped (${kind}): no justification`);
      return;
    }
    if (!byId.has(src) || !byId.has(dst)) {
      limitations.push(`edge dropped (${kind}): missing node`);
      return;
    }
    const key = `${src}|${kind}|${dst}`;
    if (edgeKeys.has(key)) return;
    edgeKeys.add(key);
    edges.push({ id: key, src, dst, kind, justification });
  };

  const invNode = addNode({
    id: `investigation:${report.investigation_id}`,
    kind: "investigation",
    label: report.investigation_id,
    accent: "kind-investigation",
    data: report,
    referencedOnly: false,
  });

  for (const toolId of report.tools_used) {
    const n = addNode({
      id: `tool:${toolId}`,
      kind: "tool",
      label: toolId,
      accent: "kind-tool",
      data: toolId,
      referencedOnly: false,
    });
    addEdge(invNode.id, n.id, "ASSOCIATED_WITH", `tools_used=${toolId}`);
  }

  for (const agentId of report.agents_used) {
    const n = addNode({
      id: `agent:${agentId}`,
      kind: "agent",
      label: agentId,
      accent: "kind-agent",
      data: agentId,
      referencedOnly: false,
    });
    addEdge(invNode.id, n.id, "ASSOCIATED_WITH", `agents_used=${agentId}`);
  }

  const evidenceById = new Map<string, Evidence>(
    report.evidence.map((e) => [e.evidence_id, e]),
  );
  for (const ev of report.evidence) {
    addNode({
      id: `evidence:${ev.evidence_id}`,
      kind: "evidence",
      label: ev.source || ev.evidence_id,
      accent: "kind-evidence",
      data: ev,
      referencedOnly: false,
    });
  }

  /** Resolve an evidence_id to a node, creating an honest stub + a
   *  declared limitation when the report lacks the full payload. */
  const evidenceNode = (eid: string): GraphNode => {
    const existing = byId.get(`evidence:${eid}`);
    if (existing) return existing;
    limitations.push(`evidence:${eid} referenced but absent from report`);
    return addNode({
      id: `evidence:${eid}`,
      kind: "evidence",
      label: eid,
      accent: "kind-evidence",
      data: eid,
      referencedOnly: true,
    });
  };

  for (const f of report.findings) {
    const fNode = addNode({
      id: `finding:${f.finding_id}`,
      kind: "finding",
      label: f.explanation.slice(0, 80) || f.finding_id,
      accent: `severity-${f.severity}`,
      data: f,
      referencedOnly: false,
    });
    addEdge(invNode.id, fNode.id, "PRODUCED", "report.findings");
    for (const eid of f.evidence_ids) {
      const eNode = evidenceNode(eid);
      addEdge(eNode.id, fNode.id, "SUPPORTED_BY", `evidence_id=${eid}`);
    }
  }

  const hypotheses = [
    ...report.hypotheses_supported,
    ...report.hypotheses_refuted,
  ];
  for (const h of hypotheses) {
    const hNode = addNode({
      id: `hypothesis:${h.hypothesis_id}`,
      kind: "hypothesis",
      label: h.statement.slice(0, 80) || h.hypothesis_id,
      accent: "kind-hypothesis",
      data: h,
      referencedOnly: false,
    });
    // RCA ids are `rca:<category>` — findings cluster by category.
    const cat = h.hypothesis_id.startsWith("rca:")
      ? h.hypothesis_id.slice(4)
      : null;
    const sup = new Set(h.supporting_evidence);
    for (const f of report.findings) {
      const shared = f.evidence_ids.filter((eid) => sup.has(eid));
      if (cat !== null && f.category === cat) {
        addEdge(
          `finding:${f.finding_id}`,
          hNode.id,
          "ASSOCIATED_WITH",
          `category=${cat}`,
        );
      } else if (shared.length) {
        addEdge(
          `finding:${f.finding_id}`,
          hNode.id,
          "ASSOCIATED_WITH",
          `shared_evidence=${shared.join(",")}`,
        );
      }
    }
    for (const eid of h.supporting_evidence) {
      const eNode = evidenceNode(eid);
      addEdge(eNode.id, hNode.id, "SUPPORTED_BY", `evidence_id=${eid}`);
    }
    for (const eid of h.contradicting_evidence) {
      // Refuting links are drawn only when the evidence node exists —
      // the label VALIDATED_BY marks the adversarial check, never a
      // causal claim.
      if (byId.has(`evidence:${eid}`)) {
        addEdge(
          `evidence:${eid}`,
          hNode.id,
          "VALIDATED_BY",
          `contradicts=${eid}`,
        );
      }
    }
  }

  if (nodes.length <= 1) {
    limitations.push(
      "report carries no findings/evidence/hypotheses to graph",
    );
  }
  // Deterministic emission order.
  nodes.sort((a, b) =>
    KIND_ORDER[a.kind] - KIND_ORDER[b.kind] || a.id.localeCompare(b.id),
  );
  edges.sort((a, b) => a.id.localeCompare(b.id));
  return { nodes, edges, limitations };
}

const KIND_ORDER: Record<GraphNodeKind, number> = {
  investigation: 0,
  tool: 1,
  agent: 2,
  evidence: 3,
  finding: 4,
  hypothesis: 5,
};

/**
 * Deterministic layered layout: longest-path layering over the DAG
 * (sources on the left), nodes inside a lane ordered by kind then id.
 * No physics, no wall-clock — identical input → identical layout.
 */
export function layoutGraph(model: GraphModel): GraphLayout {
  const byId = new Map(model.nodes.map((n) => [n.id, n]));
  const preds = new Map<string, string[]>();
  for (const e of model.edges) {
    if (!byId.has(e.src) || !byId.has(e.dst)) continue;
    const list = preds.get(e.dst);
    if (list) {
      list.push(e.src);
    } else {
      preds.set(e.dst, [e.src]);
    }
  }

  // Longest-path layering; cycles (none expected) degrade to layer 0.
  const layer = new Map<string, number>();
  const visit = (id: string, stack: Set<string>): number => {
    const memo = layer.get(id);
    if (memo !== undefined) return memo;
    if (stack.has(id)) return 0;
    stack.add(id);
    let l = 0;
    for (const p of preds.get(id) ?? []) {
      l = Math.max(l, visit(p, stack) + 1);
    }
    stack.delete(id);
    layer.set(id, l);
    return l;
  };
  for (const n of model.nodes) visit(n.id, new Set());

  const lanes = new Map<number, GraphNode[]>();
  for (const n of model.nodes) {
    const l = layer.get(n.id) ?? 0;
    (lanes.get(l) ?? lanes.set(l, []).get(l)!).push(n);
  }

  const positioned: PositionedNode[] = [];
  let maxLane = 0;
  let maxRows = 0;
  for (const [l, lane] of [...lanes.entries()].sort((a, b) => a[0] - b[0])) {
    lane.sort(
      (a, b) =>
        KIND_ORDER[a.kind] - KIND_ORDER[b.kind] ||
        a.id.localeCompare(b.id),
    );
    maxLane = Math.max(maxLane, l);
    maxRows = Math.max(maxRows, lane.length);
    lane.forEach((n, i) => {
      positioned.push({
        ...n,
        layer: l,
        x: MARGIN + l * (NODE_W + LANE_GAP),
        y: MARGIN + i * (NODE_H + ROW_GAP),
        w: NODE_W,
        h: NODE_H,
      });
    });
  }

  return {
    nodes: positioned,
    edges: model.edges,
    width: MARGIN * 2 + (maxLane + 1) * NODE_W + maxLane * LANE_GAP,
    height: MARGIN * 2 + maxRows * (NODE_H + ROW_GAP) - ROW_GAP,
  };
}
