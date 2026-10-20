"""Logical permissions graph — §5.4, ds-0024.

Nodes: principals, roles, accounts, catalogs, databases, tables, resource
links, buckets, KMS keys. Edges are typed and every edge carries a
provenance: observed | declared | inferred | unverified. Lack of visibility
is unknown — never denial.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class EdgeType(StrEnum):
    ASSUMES_ROLE = "ASSUMES_ROLE"
    REFERENCES = "REFERENCES"
    SHARES_WITH = "SHARES_WITH"
    GRANTED_ON = "GRANTED_ON"
    READS_FROM = "READS_FROM"
    WRITES_TO = "WRITES_TO"
    ENCRYPTED_BY = "ENCRYPTED_BY"


class EdgeProvenance(StrEnum):
    OBSERVED = "observed"
    DECLARED = "declared"
    INFERRED = "inferred"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class Node:
    node_id: str
    kind: str  # principal | role | account | catalog | database | table |
    #            resource_link | bucket | kms_key


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    edge_type: EdgeType
    provenance: EdgeProvenance
    note: str = ""


@dataclass
class PermissionsGraph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def add_node(self, node_id: str, kind: str) -> Node:
        if node_id and node_id not in self.nodes:
            self.nodes[node_id] = Node(node_id=node_id, kind=kind)
        return self.nodes.get(node_id) or Node("", kind)

    def add_edge(self, src: str, dst: str, t: EdgeType,
                 prov: EdgeProvenance, note: str = "") -> None:
        if src and dst:
            self.edges.append(Edge(src, dst, t, prov, note))

    def edges_of(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.src == node_id or e.dst == node_id]

    def unverified(self) -> list[Edge]:
        return [e for e in self.edges if e.provenance == EdgeProvenance.UNVERIFIED]

    def to_dict(self) -> dict[str, object]:
        return {
            "nodes": [{"id": n.node_id, "kind": n.kind} for n in self.nodes.values()],
            "edges": [
                {"src": e.src, "dst": e.dst, "type": e.edge_type.value,
                 "provenance": e.provenance.value, "note": e.note}
                for e in self.edges
            ],
        }
