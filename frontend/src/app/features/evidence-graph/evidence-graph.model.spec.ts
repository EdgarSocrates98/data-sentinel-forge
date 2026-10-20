import type { InvestigationReport } from "../../core/api.models";
import {
  buildInvestigationGraph,
  layoutGraph,
} from "./evidence-graph.model";

function report(partial: Partial<InvestigationReport>): InvestigationReport {
  return {
    report_id: "inv-x",
    investigation_id: "inv-x",
    problem: "p",
    context: {},
    agents_used: [],
    tools_used: [],
    findings: [],
    hypotheses_supported: [],
    hypotheses_refuted: [],
    conclusions: [],
    recommendations: [],
    evidence: [],
    limitations: [],
    tokens_used: 0,
    cost_usd: 0,
    duration_seconds: 0,
    ...partial,
  };
}

describe("buildInvestigationGraph", () => {
  it("links findings to the investigation and evidence via real ids", () => {
    const g = buildInvestigationGraph(
      report({
        tools_used: ["sentinel.sql.analyze"],
        agents_used: ["sentinel.sql-doctor"],
        findings: [
          {
            finding_id: "f1",
            category: "sql_antipattern",
            severity: "HIGH",
            status: "CONFIRMED",
            explanation: "SELECT * sem projeção",
            evidence_ids: ["e1"],
            alternatives: [],
            recommendations: [],
            validation_steps: [],
          },
        ],
        evidence: [
          {
            evidence_id: "e1",
            source: "sql",
            source_location: "/tmp/q.sql",
            captured_at: "2025-10-27T10:00:00Z",
            content_hash: "h",
            sanitized_excerpt: "select * from t",
            provenance: "observed",
            confidence: 0.8,
            access_metadata: null,
          },
        ],
      }),
    );

    const nodeIds = g.nodes.map((n) => n.id);
    expect(nodeIds).toContain("investigation:inv-x");
    expect(nodeIds).toContain("finding:f1");
    expect(nodeIds).toContain("evidence:e1");
    expect(nodeIds).toContain("tool:sentinel.sql.analyze");
    expect(nodeIds).toContain("agent:sentinel.sql-doctor");

    const edgeKeys = g.edges.map((e) => `${e.src}|${e.kind}|${e.dst}`);
    expect(edgeKeys).toContain(
      "investigation:inv-x|PRODUCED|finding:f1",
    );
    expect(edgeKeys).toContain("evidence:e1|SUPPORTED_BY|finding:f1");
    expect(edgeKeys).toContain(
      "investigation:inv-x|ASSOCIATED_WITH|tool:sentinel.sql.analyze",
    );
    // every edge carries a justification (no gratuitous links)
    expect(g.edges.every((e) => e.justification.length > 0)).toBeTrue();
  });

  it("links hypotheses to findings by shared RCA category and evidence", () => {
    const g = buildInvestigationGraph(
      report({
        findings: [
          {
            finding_id: "f1",
            category: "data_skew",
            severity: "MEDIUM",
            status: "PROBABLE",
            explanation: "skew",
            evidence_ids: ["e1"],
            alternatives: [],
            recommendations: [],
            validation_steps: [],
          },
        ],
        hypotheses_supported: [
          {
            hypothesis_id: "rca:data_skew",
            statement: "causa-raiz provável em 'data_skew'",
            status: "supported",
            supporting_evidence: ["e1"],
            contradicting_evidence: [],
            confidence: "PROBABLE",
            alternatives: [],
            causal_claim: false,
            causal_label: "suspected_cause",
          },
        ],
      }),
    );

    const kinds = g.edges.map((e) => `${e.kind}:${e.dst}`);
    expect(kinds).toContain("ASSOCIATED_WITH:hypothesis:rca:data_skew");
    // e1 has no payload → referenced-only stub + declared limitation
    const stub = g.nodes.find((n) => n.id === "evidence:e1");
    expect(stub?.referencedOnly).toBeTrue();
    expect(g.limitations.length).toBeGreaterThan(0);
  });

  it("declares a limitation when the report has nothing to graph", () => {
    const g = buildInvestigationGraph(report({}));
    expect(g.nodes.length).toBe(1); // only the investigation node
    expect(g.edges.length).toBe(0);
    expect(g.limitations.length).toBeGreaterThan(0);
  });
});

describe("layoutGraph", () => {
  it("is deterministic and layers sinks to the right of sources", () => {
    const g = buildInvestigationGraph(
      report({
        findings: [
          {
            finding_id: "f1",
            category: "c",
            severity: "LOW",
            status: "POSSIBLE",
            explanation: "x",
            evidence_ids: ["e1"],
            alternatives: [],
            recommendations: [],
            validation_steps: [],
          },
        ],
        evidence: [
          {
            evidence_id: "e1",
            source: "log",
            source_location: "/l",
            captured_at: "2025-10-27T10:00:00Z",
            content_hash: "h",
            sanitized_excerpt: "s",
            provenance: "observed",
            confidence: 0.5,
            access_metadata: null,
          },
        ],
      }),
    );
    const a = layoutGraph(g);
    const b = layoutGraph(g);
    expect(a).toEqual(b);

    const byId = new Map(a.nodes.map((n) => [n.id, n]));
    const evidence = byId.get("evidence:e1")!;
    const finding = byId.get("finding:f1")!;
    // evidence supports finding → finding sits in a later layer
    expect(finding.layer).toBeGreaterThan(evidence.layer);
    expect(finding.x).toBeGreaterThan(evidence.x);
    expect(a.width).toBeGreaterThan(0);
    expect(a.height).toBeGreaterThan(0);
  });
});
