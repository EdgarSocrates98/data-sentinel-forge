"""Column profiling from observed row samples (ds-0043, §5).

Profiles are built ONLY from provided samples — never fabricates.
Heavy stats use numpy when the `stats` extra is installed; otherwise a
documented stdlib fallback computes the same basic metrics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False

MAX_SAMPLE = 1_000_000


@dataclass
class ColumnProfile:
    column: str
    dtype_inferred: str
    count: int
    null_count: int
    distinct_count: int
    min_value: float | None = None
    max_value: float | None = None
    mean: float | None = None
    stddev: float | None = None
    p50: float | None = None
    p95: float | None = None
    histogram_bins: list[float] = field(default_factory=list)
    histogram_counts: list[int] = field(default_factory=list)
    top_values: dict[str, int] = field(default_factory=dict)
    engine: str = "stdlib"  # numpy | stdlib


def _numeric(values: list[Any]) -> list[float]:
    out = []
    for v in values:
        try:
            f = float(v)
            if math.isfinite(f):
                out.append(f)
        except (TypeError, ValueError):
            pass
    return out


def profile_column(column: str, values: list[Any],
                   *, top_k: int = 10) -> ColumnProfile:
    """Profile a single column from a value sample (capped)."""
    values = values[:MAX_SAMPLE]
    count = len(values)
    nulls = sum(1 for v in values if v is None or
                (isinstance(v, float) and math.isnan(v)))
    non_null = [v for v in values if not (
        v is None or (isinstance(v, float) and math.isnan(v)))]
    distinct: dict[str, int] = {}
    for v in non_null:
        k = str(v)
        distinct[k] = distinct.get(k, 0) + 1

    nums = _numeric(non_null)
    numeric_ratio = len(nums) / len(non_null) if non_null else 0.0
    dtype = "numeric" if numeric_ratio > 0.9 else (
        "boolean" if set(distinct) <= {"True", "False"} else "string")

    p = ColumnProfile(column=column, dtype_inferred=dtype, count=count,
                      null_count=nulls, distinct_count=len(distinct),
                      engine="numpy" if _HAS_NUMPY else "stdlib")
    p.top_values = dict(sorted(distinct.items(),
                               key=lambda kv: kv[1],
                               reverse=True)[:top_k])

    if dtype == "numeric" and nums:
        if _HAS_NUMPY:
            arr = np.asarray(nums)
            p.min_value = float(np.min(arr))
            p.max_value = float(np.max(arr))
            p.mean = float(np.mean(arr))
            p.stddev = float(np.std(arr, ddof=1)) if len(nums) > 1 else 0.0
            p.p50 = float(np.percentile(arr, 50))
            p.p95 = float(np.percentile(arr, 95))
            counts, edges = np.histogram(arr, bins=min(10, len(nums)))
            p.histogram_counts = counts.tolist()
            p.histogram_bins = edges.tolist()
        else:
            s = sorted(nums)
            p.min_value, p.max_value = s[0], s[-1]
            p.mean = sum(s) / len(s)
            p.stddev = (math.sqrt(
                sum((x - p.mean) ** 2 for x in s) / (len(s) - 1))
                if len(s) > 1 else 0.0)
            p.p50 = s[len(s) // 2]
            p.p95 = s[int(len(s) * 0.95)]
    return p


def profile_table(rows: list[dict[str, Any]],
                  columns: list[str] | None = None
                  ) -> dict[str, ColumnProfile]:
    """Profile all (or selected) columns from row dicts."""
    if not rows:
        return {}
    cols = columns or sorted({k for r in rows for k in r})
    out: dict[str, ColumnProfile] = {}
    for c in cols:
        out[c] = profile_column(c, [r.get(c) for r in rows])
    return out
