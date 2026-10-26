"""Spark execution plan model (§5.2).

Internal models — preserve hierarchy/order; statistics carry provenance
(estimated/declared/observed). ``to_dict`` is the stable wire shape
exposed by ``sentinel.spark.analyze_plan`` (JSON-safe).
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanNode:
    node_id: int
    operator: str  # canonical operator name, or "unknown:<raw>"
    parent_id: int | None
    children: list[int] = field(default_factory=list)
    expressions: list[str] = field(default_factory=list)
    statistics: dict[str, str] = field(default_factory=dict)
    stats_provenance: str = "declared"  # estimated | declared | observed
    source_span: tuple[int, int] = (0, 0)  # (start_line, end_line)
    raw_text: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Typed wire shape — JSON-safe, node ids as ints."""
        return {
            "node_id": self.node_id,
            "operator": self.operator,
            "parent_id": self.parent_id,
            "children": list(self.children),
            "expressions": list(self.expressions),
            "statistics": dict(self.statistics),
            "stats_provenance": self.stats_provenance,
            "source_span": list(self.source_span),
            "raw_text": self.raw_text,
            "metadata": dict(self.metadata),
        }


@dataclass
class ExecutionPlan:
    plan_id: str
    format: str  # explain_simple | explain_extended | explain_formatted | explain_cost | df_explain
    spark_version: str | None
    roots: list[int] = field(default_factory=list)
    nodes: dict[int, PlanNode] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    source: str = ""
    aqe: dict[str, str] = field(default_factory=dict)  # isFinalPlan, level markers

    def to_dict(self) -> dict[str, Any]:
        """Typed wire shape — ``nodes`` keyed by str(node_id) for JSON."""
        return {
            "plan_id": self.plan_id,
            "format": self.format,
            "spark_version": self.spark_version,
            "roots": list(self.roots),
            "nodes": {str(k): n.to_dict() for k, n in self.nodes.items()},
            "warnings": list(self.warnings),
            "source": self.source,
            "aqe": dict(self.aqe),
        }

    def children_of(self, node_id: int) -> list[PlanNode]:
        return [self.nodes[c] for c in self.nodes[node_id].children if c in self.nodes]

    def operators(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in self.nodes.values():
            counts[node.operator] = counts.get(node.operator, 0) + 1
        return counts
