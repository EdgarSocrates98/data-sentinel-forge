"""Tests for regression detection (ds-0083, §4)."""
from __future__ import annotations

from data_sentinel.core.contracts.snapshot import ExecutionSnapshot
from data_sentinel.history.regression import detect_regressions, link_changes


def snap(d: float, **kw) -> ExecutionSnapshot:
    base = {"snapshot_id": "s", "platform": "glue", "job_id": "j",
            "run_id": "r", "duration_s": d, "input_bytes": 1_000_000,
            "failure": False, "provenance": "imported"}
    base.update(kw)
    return ExecutionSnapshot(**base)


def test_relative_threshold_detects_spike() -> None:
    hist = [snap(100) for _ in range(8)]
    findings = detect_regressions(hist, snap(200))
    assert any(f["metric"] == "duration_s"
               and f["method"] == "relative_threshold" for f in findings)


def test_absolute_threshold() -> None:
    hist = [snap(100) for _ in range(8)]
    findings = detect_regressions(
        hist, snap(150), abs_thresholds={"duration_s": 120})
    assert any(f["method"] == "absolute_threshold" for f in findings)


def test_no_regression_on_normal_run() -> None:
    hist = [snap(100) for _ in range(8)]
    assert detect_regressions(hist, snap(105)) == []


def test_regression_never_claims_cause() -> None:
    hist = [snap(100) for _ in range(8)]
    findings = detect_regressions(hist, snap(300))
    for f in findings:
        assert f["causal_label"] == "suspected_cause"
        assert f["confidence"] == "POSSIBLE"
        assert any("não é causa-raiz" in lim for lim in f["limitations"])


def test_link_changes_records_not_asserts() -> None:
    prev = snap(100, runtime="g3", input_bytes=1_000_000)
    cur = snap(300, runtime="g4", input_bytes=3_000_000)
    findings = link_changes(
        detect_regressions([prev] * 5, cur), cur, [prev])
    f = findings[0]
    assert any("runtime" in c for c in f["related_changes"])
    assert any("causalidade não afirmada" in lim for lim in f["limitations"])


def test_zscore_needs_5_points() -> None:
    hist = [snap(100), snap(102), snap(98)]
    findings = detect_regressions(hist, snap(500))
    assert not any(f["method"] == "robust_zscore" for f in findings)


def test_missing_metric_skipped() -> None:
    hist = [snap(100, resource_metrics={})]
    cur = snap(200, resource_metrics={"cpu_utilization": 90})
    findings = detect_regressions(hist, cur)
    assert not any(f["metric"] == "cpu_utilization" for f in findings)
