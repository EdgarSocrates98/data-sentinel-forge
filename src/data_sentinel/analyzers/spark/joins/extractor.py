"""Join extraction from SQLGlot ASTs, plan trees and stats descriptors.

Joins found in SQL text carry the query's own span; plan-derived joins
carry the plan node id. Never executes SQL — static analysis only.
"""

import json
from dataclasses import dataclass, field
from typing import Any

import sqlglot
from sqlglot import exp

from data_sentinel.analyzers.spark.joins.models import (
    JoinForm,
    JoinSide,
    JoinSignature,
    KeyStats,
    TableStats,
)
from data_sentinel.analyzers.spark.plans.models import ExecutionPlan

_FORM_MAP = {
    "": JoinForm.INNER,
    "INNER": JoinForm.INNER,
    "LEFT": JoinForm.LEFT,
    "LEFT OUTER": JoinForm.LEFT,
    "RIGHT": JoinForm.RIGHT,
    "RIGHT OUTER": JoinForm.RIGHT,
    "FULL": JoinForm.FULL,
    "FULL OUTER": JoinForm.FULL,
    "CROSS": JoinForm.CROSS,
    "SEMI": JoinForm.SEMI,
    "LEFT SEMI": JoinForm.SEMI,
    "ANTI": JoinForm.ANTI,
    "LEFT ANTI": JoinForm.ANTI,
}

_INEQUALITY_NODES = (
    exp.GTE,
    exp.GT,
    exp.LTE,
    exp.LT,
    exp.NEQ,
    exp.Between,
    exp.Like,
    exp.ILike,
)


@dataclass
class JoinContext:
    joins: list[JoinSignature] = field(default_factory=list)
    stats: dict[str, TableStats] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _table_name(node: exp.Expr | None) -> str:
    if node is None:
        return "unknown"
    if isinstance(node, exp.Table):
        return node.name or node.alias_or_name or "unknown"
    return getattr(node, "alias_or_name", None) or node.sql()[:40]


def _eq_keys(on: exp.Expr | None) -> list[tuple[str, str]]:
    """Equality key pairs (left_col, right_col) from EQ conjuncts."""
    out: list[tuple[str, str]] = []
    if on is None:
        return out
    for eq in on.find_all(exp.EQ):
        cols = list(eq.find_all(exp.Column))
        if len(cols) == 2:
            out.append((cols[0].sql(), cols[1].sql()))
    return out


def _has_inequality(on: exp.Expr | None) -> bool:
    if on is None:
        return False
    return any(on.find(kind) is not None for kind in _INEQUALITY_NODES)


def _is_expression_based(on: exp.Expr | None) -> bool:
    """Join keys that are not bare column references."""
    if on is None:
        return False
    for eq in on.find_all(exp.EQ):
        for side in (eq.left, eq.right):
            if not isinstance(side, exp.Column):
                return True
    return False


def extract_from_sql(sql_text: str, *, dialect: str = "spark") -> JoinContext:
    ctx = JoinContext()
    try:
        tree = sqlglot.parse_one(sql_text, dialect=dialect)
    except Exception as exc:  # sqlglot ParseError + tokenizer errors
        ctx.warnings.append(f"SQL não parseado como dialeto '{dialect}': {exc}")
        return ctx
    if tree is None:
        ctx.warnings.append("SQL vazio ou não reconhecido")
        return ctx

    for n, join in enumerate(tree.find_all(exp.Join), start=1):
        kind = str(join.args.get("kind") or "").upper()
        side = str(join.args.get("side") or "").upper()
        combined = f"{side} {kind}".strip()
        form = _FORM_MAP.get(combined, _FORM_MAP.get(kind, JoinForm.OTHER))

        on = join.args.get("on")
        parent = join.parent
        if isinstance(parent, exp.Select):
            siblings = parent.args.get("joins") or []
            frm = parent.args.get("from_")
            if siblings and join is siblings[0] and frm is not None:
                left_table = _table_name(frm.this)
            else:
                left_table = "junção-anterior"
        else:
            left_table = "unknown"
        this_table = _table_name(join.this)

        eq = _eq_keys(on)
        ctx.joins.append(
            JoinSignature(
                join_id=f"sql-join-{n}",
                form=form,
                left=JoinSide(table=left_table, keys=[k[0] for k in eq]),
                right=JoinSide(table=this_table, keys=[k[1] for k in eq]),
                condition=on.sql() if on is not None else "",
                equality_keys=eq,
                is_inequality=_has_inequality(on),
                is_expression_based=_is_expression_based(on),
                source="sql",
            )
        )
    return ctx


_PLAN_JOIN_OPS = {
    "SortMergeJoin",
    "BroadcastHashJoin",
    "ShuffledHashJoin",
    "BroadcastNestedLoopJoin",
    "CartesianProduct",
}


def extract_from_plan(plan: ExecutionPlan) -> JoinContext:
    ctx = JoinContext()
    for node in plan.nodes.values():
        if node.operator not in _PLAN_JOIN_OPS:
            continue
            form = (
                JoinForm.CROSS
                if node.operator == "CartesianProduct"
                else JoinForm.OTHER
            )
            ctx.joins.append(
                JoinSignature(
                    join_id=f"plan-join-{node.node_id}",
                    form=form,
                    left=JoinSide(table="unknown"),
                    right=JoinSide(table="unknown"),
                    condition=node.raw_text,
                    source="plan",
                    source_span=node.source_span,
                )
            )
    return ctx


def load_stats(text: str) -> tuple[dict[str, TableStats], dict[str, Any], list[str]]:
    """Load a stats descriptor (JSON). Malformed input → warning, no raise.

    Returns (tables, runtime_metrics, warnings). runtime_metrics carries
    observed operational values (task durations, shuffle skew flags) —
    never statistics we fabricated.
    """
    warnings: list[str] = []
    try:
        raw: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as exc:
        return {}, {}, [f"descritor de estatísticas inválido: {exc}"]

    out: dict[str, TableStats] = {}
    for name, meta in (raw.get("tables") or {}).items():
        if not isinstance(meta, dict):
            warnings.append(f"tabela '{name}' ignorada — metadados não-objeto")
            continue
        keys = {}
        for col, k in (meta.get("keys") or {}).items():
            keys[col] = KeyStats(
                column=col,
                distinct=k.get("distinct"),
                null_fraction=k.get("null_fraction"),
                source=k.get("source", "declared"),
            )
        out[name] = TableStats(
            name=name,
            row_count=meta.get("row_count"),
            keys=keys,
            top_keys=list(meta.get("top_keys") or []),
            source=meta.get("source", "declared"),
        )
    runtime_raw = raw.get("runtime")
    runtime: dict[str, Any] = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    return out, runtime, warnings
