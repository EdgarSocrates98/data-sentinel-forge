"""Glue/FGAC/FTA compatibility engine — §4, ds-0023.

Evaluates (runtime, spark, iceberg, catalog, access_mode, operation) against
the packaged knowledge base → CompatibilityAssessment with evidence and
references. Access modes are never presumed: "unknown" stays unknown.
Rules are per-version — support is never generalized across runtimes.
"""

from datetime import datetime

from data_sentinel.core.contracts.entities import DiagnosticRequest, Evidence
from data_sentinel.core.contracts.enums import (
    EvidenceProvenance,
    SupportStatus,
)
from data_sentinel.core.contracts.lakehouse import (
    AccessContext,
    CompatibilityAssessment,
)
from data_sentinel.knowledge.engine import select
from data_sentinel.knowledge.schema import Rule, load_packaged_rules

KNOWN_ACCESS_MODES = ("iam", "fgac", "fta", "legacy", "unknown")
SUPPORTED_OPERATIONS = (
    "select", "insert", "append", "update", "delete", "merge",
    "create", "alter", "drop", "describe", "metadata", "maintenance",
)


def _ctx(runtime: str, table_format: str, access_mode: str, operation: str,
         catalog: str) -> dict[str, str]:
    return {
        "service": "aws_glue",
        "engine": "spark",
        "runtime": runtime,
        "table_format": table_format,
        "access_mode": access_mode,
        "operation": operation,
        "catalog": catalog,
    }


def _evidence(rule: Rule, captured: datetime) -> Evidence:
    return Evidence(
        source="knowledge_rule",
        source_location=f"knowledge/rules/{rule.rule_id}@{rule.version}",
        captured_at=captured,
        content_hash=f"rule:{rule.rule_id}:{rule.version}",
        sanitized_excerpt=(
            f"regra {rule.rule_id} v{rule.version} → {rule.status.value}; "
            f"{rule.constraints[:180]}"
        ),
        provenance=EvidenceProvenance.DECLARED,
        confidence=0.7,
    )


def assess_compatibility(
    request: DiagnosticRequest | None,
    *,
    runtime: str,
    spark_version: str = "",
    iceberg_version: str = "",
    table_format: str = "iceberg",
    catalog: str = "",
    access_mode: str = "unknown",
    operation: str,
    access_context: AccessContext | None = None,
    rules: list[Rule] | None = None,
) -> CompatibilityAssessment:
    """Assess compatibility of one operation tuple.

    Never presumes access mode: if `access_mode` is "unknown" and the
    AccessContext carries no visible mode, result stays UNKNOWN/NOT_VERIFIED
    per rule coverage — FGAC is never inferred.
    """
    from datetime import UTC, datetime

    captured = datetime.now(UTC)
    if rules is None:
        rules, load_errors = load_packaged_rules()
    else:
        load_errors = []

    mode = access_mode if access_mode in KNOWN_ACCESS_MODES else "unknown"
    op = operation.lower()
    constraints: list[str] = []
    evidence: list[Evidence] = []
    refs: list[str] = []

    # 1) runtime x format matrix first (operation-agnostic)
    matrix = select(rules, _ctx(runtime, table_format, mode, "*", catalog))
    if matrix.rule is not None:
        evidence.append(_evidence(matrix.rule, captured))
        refs.extend(matrix.rule.references)
        base_status = matrix.rule.status
        if matrix.rule.constraints:
            constraints.append(matrix.rule.constraints.strip())
    else:
        base_status = SupportStatus.UNKNOWN

    # 2) access-mode layer (only when a mode is known — never presume fgac)
    if mode != "unknown":
        mode_match = select(rules, _ctx(runtime, table_format, mode, "*", catalog))
        if mode_match.rule is not None and mode_match.rule.access_mode:
            evidence.append(_evidence(mode_match.rule, captured))
            refs.extend(mode_match.rule.references)
            if mode_match.rule.constraints:
                constraints.append(mode_match.rule.constraints.strip())
            # most restrictive of matrix+mode wins
            order = [SupportStatus.UNSUPPORTED, SupportStatus.UNKNOWN,
                     SupportStatus.NOT_VERIFIED,
                     SupportStatus.SUPPORTED_WITH_CONSTRAINTS,
                     SupportStatus.SUPPORTED]
            base_status = min(base_status, mode_match.rule.status, key=order.index)
    else:
        constraints.append(
            "Modo de acesso não identificado — FGAC nunca é presumido; "
            "resolva iam/fgac/fta via Lake Formation ou contexto declarado."
        )
        if base_status == SupportStatus.SUPPORTED:
            base_status = SupportStatus.SUPPORTED_WITH_CONSTRAINTS

    # 3) operation-specific rule, when it exists
    op_match = select(rules, _ctx(runtime, table_format, mode, op, catalog))
    if op_match.rule is not None and op_match.rule.operation not in ("", "*"):
        evidence.append(_evidence(op_match.rule, captured))
        refs.extend(op_match.rule.references)
        if op_match.rule.constraints:
            constraints.append(op_match.rule.constraints.strip())
        order = [SupportStatus.UNSUPPORTED, SupportStatus.UNKNOWN,
                 SupportStatus.NOT_VERIFIED,
                 SupportStatus.SUPPORTED_WITH_CONSTRAINTS,
                 SupportStatus.SUPPORTED]
        base_status = min(base_status, op_match.rule.status, key=order.index)

    # 4) conflicts from the engine (ties) — surfaced, never hidden
    for match in (matrix, op_match):
        for c in match.conflicts:
            constraints.append(
                f"Contradição documental: {c} — revisão humana registrada "
                "necessária antes de confiar no veredito."
            )
            base_status = SupportStatus.UNKNOWN

    for e in load_errors:
        constraints.append(f"Base de regras: {e}")
    if op not in SUPPORTED_OPERATIONS:
        constraints.append(
            f"Operação '{operation}' fora da taxonomia conhecida "
            f"{SUPPORTED_OPERATIONS} — avaliação por regras genéricas."
        )

    # dedupe constraints preservando ordem
    seen_c: set[str] = set()
    deduped: list[str] = []
    for c in constraints:
        if c not in seen_c:
            seen_c.add(c)
            deduped.append(c)
    constraints = deduped

    return CompatibilityAssessment(
        runtime=runtime,
        spark_version=spark_version,
        iceberg_version=iceberg_version,
        catalog_type=catalog,
        access_mode=mode,
        operation=op,
        support_status=base_status,
        constraints=constraints,
        evidence=evidence,
        documentation_references=sorted(set(refs)),
    )
