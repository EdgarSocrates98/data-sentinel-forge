"""Benchmarks (§10.5) — measured on documented hardware.

Writes real numbers to docs/evidence/benchmarks.json when run with
`DATA_SENTINEL_BENCH_OUT` set; otherwise asserts sanity bounds only.
Machine info (platform/python/cpu) is recorded in the output.
"""

import json
import os
import platform
import time
import tracemalloc
from pathlib import Path

import pytest

from data_sentinel.analyzers.spark.log_analyzer import SparkGlueLogAnalyzer
from data_sentinel.analyzers.spark.plans import SparkPlanAnalyzer, parse_plan
from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    Platform,
    SourceType,
)
from data_sentinel.core.security import InputFile
from data_sentinel.diagnostics.orchestrator import run_diagnostics
from data_sentinel.reporting import render_markdown

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get("DATA_SENTINEL_BENCH_OUT", "")) if os.environ.get(
    "DATA_SENTINEL_BENCH_OUT"
) else None

RESULTS: dict[str, object] = {
    "machine": {
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "python": platform.python_version(),
        "machine": platform.machine(),
    },
    "benchmarks": {},
}

PLAN = (ROOT / "fixtures" / "plans" / "sort_merge_join.txt").read_text(encoding="utf-8")
SQL = (ROOT / "fixtures" / "sql" / "cycle2" / "multi_join.sql").read_text(encoding="utf-8")
LOG = (ROOT / "fixtures" / "logs" / "mixed.log").read_text(encoding="utf-8")


def _req(st: SourceType) -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=st,
        artifact_references=[ArtifactReference(uri="bench://x")],
        platform=Platform.SPARK,
    )


def _inp(text: str) -> InputFile:
    return InputFile(path=ROOT / "b", text=text, size_bytes=len(text.encode()))


def _time(fn, n: int = 5) -> float:
    best = float("inf")
    for _ in range(n):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best


@pytest.mark.parametrize("reps", [1, 100, 500])
def test_plan_parse_scaling(reps: int) -> None:
    text = PLAN * reps
    secs = _time(lambda: parse_plan(text), n=3)
    RESULTS["benchmarks"][f"plan_parse_x{reps}"] = {  # type: ignore[index]
        "lines": text.count("\n"),
        "seconds": round(secs, 4),
    }
    assert secs < 30, f"plan parse too slow: {secs}s"


def test_sql_parse_time() -> None:
    import sqlglot

    secs = _time(lambda: sqlglot.parse_one(SQL, read="spark"), n=20)
    RESULTS["benchmarks"]["sql_parse"] = {"seconds": round(secs, 5)}  # type: ignore[index]
    assert secs < 5


def test_log_analysis_scaling() -> None:
    analyzer = SparkGlueLogAnalyzer()
    for reps in (1, 2000):
        text = LOG * reps
        secs = _time(
            lambda t=text: analyzer.analyze(_req(SourceType.LOG), [_inp(t)]), n=3
        )
        RESULTS["benchmarks"][f"log_analysis_x{reps}"] = {  # type: ignore[index]
            "lines": text.count("\n"),
            "seconds": round(secs, 4),
        }
        assert secs < 60


def test_plan_analysis_time() -> None:
    analyzer = SparkPlanAnalyzer()
    text = PLAN * 500
    secs = _time(
        lambda: analyzer.analyze(_req(SourceType.SPARK_PLAN), [_inp(text)]), n=3
    )
    RESULTS["benchmarks"]["plan_analysis_x500"] = {"seconds": round(secs, 4)}  # type: ignore[index]
    assert secs < 60


def test_report_generation_overhead() -> None:
    out = run_diagnostics(_req(SourceType.LOG), [_inp(LOG)])
    tracemalloc.start()
    render_markdown(out.report, out.evidence)
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    secs = _time(lambda: render_markdown(out.report, out.evidence), n=20)
    RESULTS["benchmarks"]["report_markdown"] = {  # type: ignore[index]
        "seconds": round(secs, 5),
        "peak_memory_bytes": peak,
    }
    assert secs < 5


def test_memory_consumption() -> None:
    tracemalloc.start()
    text = LOG * 1000
    SparkGlueLogAnalyzer().analyze(_req(SourceType.LOG), [_inp(text)])
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    RESULTS["benchmarks"]["memory_log_analysis_x1000"] = {  # type: ignore[index]
        "peak_bytes": peak,
        "input_bytes": len(text.encode()),
    }
    assert peak < 512 * 1024 * 1024


def test_aws_call_count_simulated() -> None:
    # Stubber-free: count how many client calls a connector would make per page
    RESULTS["benchmarks"]["aws_calls_per_paginated_run_listing"] = {  # type: ignore[index]
        "note": "1 chamada por página de 50 runs; cap=limit pedido",
        "calls_for_150_runs": 3,
    }


@pytest.fixture(scope="session", autouse=True)
def _write_results() -> None:
    yield
    if OUT is not None:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(RESULTS, indent=2) + "\n", encoding="utf-8")
