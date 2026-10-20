"""Spark plan text parser (§5.1/§5.8).

Pure-Python, tolerant parser for EXPLAIN / DataFrame.explain output. No eval,
no dynamic execution. Unknown operators become typed unknown nodes and
recorded as warnings — never abort the parse.
"""

import re
import uuid

from data_sentinel.analyzers.spark.plans.models import ExecutionPlan, PlanNode

# Operators recognized per §5.3 (plus common Glue/Spark aliases).
KNOWN_OPERATORS: dict[str, str] = {
    "Scan": "Scan",
    "FileScan": "Scan",
    "BatchScan": "Scan",
    "InMemoryTableScan": "Scan",
    "Filter": "Filter",
    "Project": "Project",
    "HashAggregate": "HashAggregate",
    "SortAggregate": "SortAggregate",
    "ObjectHashAggregate": "HashAggregate",
    "Sort": "Sort",
    "Exchange": "Exchange",
    "BroadcastExchange": "BroadcastExchange",
    "BroadcastHashJoin": "BroadcastHashJoin",
    "SortMergeJoin": "SortMergeJoin",
    "ShuffledHashJoin": "ShuffledHashJoin",
    "CartesianProduct": "CartesianProduct",
    "BroadcastNestedLoopJoin": "BroadcastNestedLoopJoin",
    "Repartition": "Repartition",
    "Coalesce": "Coalesce",
    "Union": "Union",
    "Window": "Window",
    "AdaptiveSparkPlan": "AdaptiveSparkPlan",
    "Generate": "Generate",
    "Expand": "Expand",
    "ColumnarToRow": "ColumnarToRow",
    "InputAdapter": "InputAdapter",
    "SubqueryBroadcast": "SubqueryBroadcast",
    "Execute InsertIntoHadoopFsRelationCommand": "Write",
    "TakeOrderedAndProject": "TakeOrderedAndProject",
    "GlobalLimit": "GlobalLimit",
    "LocalLimit": "LocalLimit",
    "CollectLimit": "CollectLimit",
    "WholeStageCodegen": "WholeStageCodegen",
    "EvalPython": "EvalPython",
}

# Tree markers: "+- "/":- " open a child node; "|"/":"+spaces are guides.
# Depth = (marker index + 3) // 3 — Spark indents each level by 3 columns.
_MARKER = re.compile(r"(\+-|:- )")
_STAGE_TAG = re.compile(r"^\*\(\d+\)\s*")
_FIRST_WORD = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)")
_STAT_KV = re.compile(r"([A-Za-z_][\w.]*)\s*=\s*([^,\]\)]{1,200})")
_STATS_SCAN_LIMIT = 8192
_KNOWN_FORMAT_MARKERS = (
    ("explain_formatted", re.compile(r"^\s*\(\d+\)")),
    ("explain_cost", re.compile(r"Plan with statistics|Optimized Logical Plan", re.I)),
    ("df_explain", re.compile(r"^== Physical Plan ==", re.M)),
    ("explain_extended", re.compile(r"==.*(Logical|Physical) Plan.*==|Parsed Logical Plan")),
)


def detect_format(text: str) -> str:
    """Best-effort format detection from content markers."""
    for name, regex in _KNOWN_FORMAT_MARKERS:
        if regex.search(text):
            return name
    return "df_explain"


def _split_node_line(line: str) -> tuple[int, str] | None:
    """Return (depth, content) for tree node lines, else None."""
    m = _MARKER.search(line)
    if m is not None and set(line[: m.start()]) <= set("|: "):
        content = line[m.end() :]
        return (m.start() + 3) // 3, content
    if line and not line[0].isspace() and not line.startswith("=="):
        return 0, line
    return None


def _operator_of(content: str) -> str | None:
    """First-word operator name, or multiword command prefix."""
    content = _STAGE_TAG.sub("", content.lstrip()).lstrip()
    m = _FIRST_WORD.match(content)
    if m is None:
        return None
    word = m.group(1)
    if word == "Execute":
        words = content.split()
        return " ".join(words[: min(3, len(words))])
    return word


def _parse_stats(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    # Scan only a bounded prefix: stats k=v pairs are short, and an unbounded
    # scan makes _STAT_KV quadratic on huge single-line inputs.
    for m in _STAT_KV.finditer(raw[:_STATS_SCAN_LIMIT]):
        key = m.group(1)
        if key in ("id", "name", "plan_id"):
            continue
        out[key] = m.group(2).strip()
    return out


def parse_plan(text: str, *, source: str = "") -> ExecutionPlan:
    """Parse plan text into an ExecutionPlan — never raises on bad input."""
    plan = ExecutionPlan(
        plan_id=uuid.uuid4().hex[:16],
        format=detect_format(text),
        spark_version=None,
        source=source,
    )
    lines = text.splitlines()
    stack: list[tuple[int, int]] = []  # (depth, node_id)
    next_id = 0
    section_depth: int | None = None

    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("==") and line.endswith("=="):
            continue  # section header
        m_ver = re.search(r"spark\.version[=: ]+([0-9.]+)", line, re.I)
        if m_ver:
            plan.spark_version = m_ver.group(1)

        split = _split_node_line(line)
        if split is None:
            if stack:
                node = plan.nodes[stack[-1][1]]
                node.raw_text += "\n" + line
                node.source_span = (node.source_span[0], lineno)
            continue
        depth, content = split

        op_raw = _operator_of(content)
        if op_raw is None:
            if stack:
                node = plan.nodes[stack[-1][1]]
                node.raw_text += "\n" + line
                node.source_span = (node.source_span[0], lineno)
            continue

        canonical = KNOWN_OPERATORS.get(op_raw)
        if canonical is None:
            canonical = f"unknown:{op_raw.split('(')[0].split()[0]}"
            plan.warnings.append(
                f"operador desconhecido '{op_raw}' na linha {lineno} — preservado como {canonical}"
            )

        node = PlanNode(
            node_id=next_id,
            operator=canonical,
            parent_id=None,
            expressions=[content[:200]],
            statistics=_parse_stats(content),
            source_span=(lineno, lineno),
            raw_text=content,
        )
        if op_raw == "AdaptiveSparkPlan" or canonical == "AdaptiveSparkPlan":
            m_final = re.search(r"isFinalPlan=(\w+)", content)
            plan.aqe = {"isFinalPlan": m_final.group(1) if m_final else "unknown"}
            node.metadata["aqe"] = "true"
        if "Statistics" in content or "sizeInBytes" in content or "rowCount" in content:
            node.stats_provenance = "estimated"

        # attach to parent by depth
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if stack:
            parent = plan.nodes[stack[-1][1]]
            node.parent_id = parent.node_id
            parent.children.append(node.node_id)
        else:
            plan.roots.append(node.node_id)
        stack.append((depth, node.node_id))
        plan.nodes[node.node_id] = node
        next_id += 1

    if section_depth is not None:  # pragma: no cover - defensive
        pass
    if not plan.nodes and lines:
        plan.warnings.append("nenhum operador identificado — texto não parece um plano Spark")
    return plan
