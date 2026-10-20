"""Tests for operational history comparison (ds-0082, §3)."""

from __future__ import annotations

from data_sentinel.core.contracts.snapshot import (
    BaselineKind,
    ExecutionSnapshot,
)
from data_sentinel.history import (
    check_comparable,
    compare_snapshots,
    select_baseline,
)


def snap(**kw) -> ExecutionSnapshot:  # type: ignore[no-untyped-def]
    base = {"snapshot_id": "s", "platform": "glue", "job_id": "j1",
            "run_id": "r1", "runtime": "glue4", "duration_s": 100.0,
            "input_bytes": 1_000_000, "failure": False,
            "config_fingerprint": "fp1", "provenance": "imported"}
    base.update(kw)
    return ExecutionSnapshot(**base)


def test_comparable_same_workload() -> None:
    assert check_comparable(snap(), snap(run_id="r2",
                                         duration_s=120.0)) == []


def test_different_platform_incomparable() -> None:
    assert "platform differs" in check_comparable(
        snap(), snap(platform="emr-ec2"))[0]


def test_different_job_incomparable() -> None:
    reasons = check_comparable(snap(), snap(job_id="other"))
    assert any("different jobs" in r for r in reasons)


def test_volume_10x_incomparable() -> None:
    reasons = check_comparable(
        snap(input_bytes=1_000_000), snap(input_bytes=20_000_000))
    assert any("volume differs" in r for r in reasons)


def test_missing_duration_incomparable() -> None:
    reasons = check_comparable(snap(), snap(duration_s=None))
    assert any("metric unavailable" in r for r in reasons)


def test_compare_produces_deltas() -> None:
    base = [snap(run_id=f"r{i}", duration_s=d, input_bytes=1_000_000)
            for i, d in enumerate([90, 100, 110])]
    cur = snap(run_id="now", duration_s=150.0, input_bytes=1_050_000,
               resource_metrics={"dpu_hours": 2.0})
    res = compare_snapshots(cur, base)
    assert res.comparable
    assert res.duration_delta_s == 50.0
    assert res.volume_delta_input == 50_000
    assert res.resource_deltas == {}  # baseline has no dpu_hours


def test_failure_regression_flag() -> None:
    base = [snap(failure=False)]
    res = compare_snapshots(snap(failure=True), base)
    assert res.failure_regression is True


def test_failure_regression_not_claimed_when_baseline_failed() -> None:
    res = compare_snapshots(snap(failure=True), [snap(failure=True)])
    assert res.failure_regression is False


def test_no_baseline_honest() -> None:
    res = compare_snapshots(snap(), [])
    assert res.comparable is False
    assert any("no baseline" in r for r in res.incomparability_reasons)


def test_select_baseline_kinds() -> None:
    snaps = [snap(run_id=f"r{i}", started_at=f"2026-01-0{i}T00:00:00Z")
             for i in range(1, 6)]
    assert len(select_baseline(snaps, BaselineKind(kind="previous"))) == 1
    assert len(select_baseline(
        snaps, BaselineKind(kind="rolling", window=3))) == 3
    assert select_baseline(
        snaps, BaselineKind(kind="reference",
                            reference_run_id="r3"))[0].run_id == "r3"
    assert len(select_baseline(snaps, BaselineKind(kind="cohort"))) == 5


def test_config_drift_detected() -> None:
    res = compare_snapshots(
        snap(config_fingerprint="fp2"), [snap(config_fingerprint="fp1")])
    assert not res.comparable  # fp diff → incomparable per §3.4
