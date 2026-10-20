"""Lakehouse context resolver — §2.3, ds-0027.

Aggregates evidence produced by the domain analyzers (Iceberg metadata,
access context, policies, operations) plus a CompatibilityAssessment into
one resolved view. Everything it cannot resolve stays UNKNOWN — the
resolver never fills gaps with guesses.
"""

from dataclasses import dataclass, field

from data_sentinel.analyzers.protocol import AnalysisResult
from data_sentinel.core.contracts.entities import Evidence, Finding
from data_sentinel.core.contracts.enums import SupportStatus
from data_sentinel.core.contracts.lakehouse import (
    AccessContext,
    CompatibilityAssessment,
)


@dataclass
class LakehouseContext:
    """Resolved view across all lakehouse inputs for one request."""

    access: AccessContext | None = None
    assessments: list[CompatibilityAssessment] = field(default_factory=list)
    iceberg_tables: list[dict[str, object]] = field(default_factory=list)
    graphs: list[dict[str, object]] = field(default_factory=list)
    evaluations: list[dict[str, object]] = field(default_factory=list)
    operations: list[dict[str, object]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    @property
    def worst_status(self) -> SupportStatus:
        """Most conservative status across assessments."""
        order = [SupportStatus.UNSUPPORTED, SupportStatus.UNKNOWN,
                 SupportStatus.NOT_VERIFIED,
                 SupportStatus.SUPPORTED_WITH_CONSTRAINTS,
                 SupportStatus.SUPPORTED]
        if not self.assessments:
            return SupportStatus.NOT_VERIFIED
        return min((a.support_status for a in self.assessments), key=order.index)

    def to_dict(self) -> dict[str, object]:
        return {
            "worst_status": self.worst_status.value,
            "assessments": [a.model_dump(mode="json") for a in self.assessments],
            "iceberg_tables": self.iceberg_tables,
            "graphs": [{k: v for k, v in g.items() if k != "graph"} for g in self.graphs],
            "evaluations": self.evaluations,
            "operations": self.operations,
            "access": self.access.model_dump(mode="json") if self.access else None,
            "findings": len(self.findings),
            "limitations": self.limitations,
        }


def resolve(
    results: list[AnalysisResult],
    assessments: list[CompatibilityAssessment] | None = None,
    access: AccessContext | None = None,
) -> LakehouseContext:
    """Fold analyzer results + assessments into one resolved context.

    `results` are AnalysisResult objects from the domain analyzers; their
    metadata tables/graphs/evaluations/operations blocks are merged.
    """
    ctx = LakehouseContext(access=access)
    if assessments:
        ctx.assessments.extend(assessments)
    for r in results:
        ctx.findings.extend(r.findings)
        ctx.evidence.extend(r.evidence)
        ctx.limitations.extend(r.limitations)
        meta = r.metadata or {}
        for key, target in (
            ("tables", ctx.iceberg_tables),
            ("graphs", ctx.graphs),
            ("evaluations", ctx.evaluations),
            ("operations", ctx.operations),
        ):
            items = meta.get(key, [])
            if isinstance(items, list):
                target.extend(i for i in items if isinstance(i, dict))
    return ctx
