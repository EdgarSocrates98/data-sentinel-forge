"""Tests for Sentinel Watch (ds-0084, §5)."""
from __future__ import annotations

import pytest

from data_sentinel.core.contracts.snapshot import ExecutionSnapshot
from data_sentinel.watch import AlertEngine, WatchDefinition, WatchRuntime
from data_sentinel.watch.engine import MIN_INTERVAL_S


def snap(d=100.0, fail=False) -> ExecutionSnapshot:
    return ExecutionSnapshot(snapshot_id="s", platform="glue",
                             job_id="j", duration_s=d, failure=fail,
                             provenance="test")


def watch(**kw) -> WatchDefinition:
    base = {"watch_id": "w1", "workload": "job", "platform": "glue",
            "source": "local", "interval_s": 60}
    base.update(kw)
    return WatchDefinition(**base)


def test_failure_alert_and_recovery() -> None:
    e = AlertEngine(cooldown_s=0)
    w = watch()
    alerts = e.evaluate(w, [snap()], snap(fail=True))
    assert any(a.kind == "job_failure" for a in alerts)
    rec = e.evaluate(w, [snap(fail=True)], snap(fail=False))
    assert any(a.recovered for a in rec)


def test_cooldown_suppresses_duplicates() -> None:
    e = AlertEngine(cooldown_s=3600)
    w = watch()
    e.evaluate(w, [snap()], snap(fail=True))
    again = e.evaluate(w, [snap()], snap(fail=True))
    assert not any(a.kind == "job_failure" for a in again)


def test_missing_data_declared_not_silent() -> None:
    e = AlertEngine()
    alerts = e.evaluate(watch(), [], snap(d=None))
    assert any(a.kind == "missing_data" and a.severity == "INFO"
               for a in alerts)


def test_register_bounds() -> None:
    rt = WatchRuntime(engine=AlertEngine(), max_watches=2)
    rt.register(watch(watch_id="a"), lambda: ([snap()], snap()))
    rt.register(watch(watch_id="b"), lambda: ([snap()], snap()))
    with pytest.raises(ValueError, match="limit"):
        rt.register(watch(watch_id="c"), lambda: ([snap()], snap()))


def test_min_interval_enforced() -> None:
    rt = WatchRuntime()
    with pytest.raises(ValueError, match="below min"):
        rt.register(watch(interval_s=5), lambda: ([snap()], snap()))


def test_run_once_idempotent() -> None:
    rt = WatchRuntime()
    calls = []
    def collect() -> tuple:
        calls.append(1)
        return ([snap()], snap(fail=True))
    rt.register(watch(), collect)
    a1 = rt.run_once("w1")
    assert a1 and calls


def test_runtime_start_stop() -> None:
    rt = WatchRuntime()
    rt.register(watch(interval_s=MIN_INTERVAL_S),
                lambda: ([snap()], snap()))
    rt.start()
    assert rt._thread and rt._thread.is_alive()
    rt.stop(timeout=3)
    assert not rt._thread.is_alive()
