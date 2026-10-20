"""Watch runtime + alert engine (§5).

Local thread scheduler: bounded (max watches, min interval, per-check
timeout, backoff on error), idempotent, cancellable. Cloud polling is
opt-in and never starts silently — a watch's ``collector`` callable is
injected by the caller; absent collector means the watch evaluates only
explicitly-fed snapshots.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from data_sentinel.core.contracts.snapshot import ExecutionSnapshot
from data_sentinel.history.regression import detect_regressions

MIN_INTERVAL_S = 30.0
MAX_WATCHES = 50


@dataclass
class WatchDefinition:
    """§5.1 — what to monitor and how."""
    watch_id: str
    workload: str
    platform: str
    source: str  # "local" | "import" | "aws" (aws requires opt-in)
    metrics: list[str] = field(default_factory=list)
    rule: str = "regression"  # regression | failure | threshold
    interval_s: float = 300.0
    severity: str = "MEDIUM"
    enabled: bool = True
    retention_s: float = 7 * 86400.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """One emitted alert (§5.4)."""
    alert_id: str
    watch_id: str
    kind: str  # job_failure | sla_breach | duration_regression |
    # quality_regression | freshness | cost_anomaly | retries | saturation
    severity: str
    message: str
    ts: float
    dedup_key: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    recovered: bool = False


class AlertEngine:
    """Dedup + cooldown + recovery tracking (§5.5)."""

    def __init__(self, cooldown_s: float = 900.0) -> None:
        self.cooldown_s = cooldown_s
        self._last_emit: dict[str, float] = {}
        self._open: dict[str, Alert] = {}
        self.history: list[Alert] = []

    def evaluate(self, watch: WatchDefinition,
                 history: list[ExecutionSnapshot],
                 current: ExecutionSnapshot) -> list[Alert]:
        """Evaluate one check — returns alerts to emit (deduped)."""
        out: list[Alert] = []
        findings = detect_regressions(history, current)

        if current.failure is True:
            out.append(self._mk(watch, "job_failure",
                                f"{watch.workload} falhou",
                                dedup="failure"))
        fail_key = f"{watch.watch_id}:failure"
        if current.failure is False and fail_key in self._open:
            out.append(self._recover(watch, "failure"))

        for f in findings:
            kind = _kind_for(str(f["metric"]))
            out.append(self._mk(
                watch, kind,
                f"{watch.workload}: {f['metric']} "
                f"{f['rationale']}", dedup=str(f["metric"]),
                findings=[f]))

        # missing-data behavior (§5.5): declare it, don't alert silently.
        # Fires only when the evaluation produced NO other signal —
        # a recovery or regression already carries the state; missing_data
        # must never compete with them in the same eval (Cycle 08.1 §7.3).
        if (current.duration_s is None and not current.resource_metrics
                and not out):
            out.append(self._mk(watch, "missing_data",
                                f"{watch.workload}: sem métricas "
                                "suficientes — UNKNOWN", dedup="missing",
                                sev="INFO"))
        return self._dedupe(out)

    def _kind_sev(self, watch: WatchDefinition, sev: str | None) -> str:
        return sev or watch.severity

    def _mk(self, watch: WatchDefinition, kind: str, msg: str,
            *, dedup: str, sev: str | None = None,
            findings: list[dict[str, Any]] | None = None) -> Alert:
        key = f"{watch.watch_id}:{dedup}"
        return Alert(
            alert_id=f"alert-{int(time.time() * 1000)}",
            watch_id=watch.watch_id, kind=kind,
            severity=self._kind_sev(watch, sev), message=msg,
            ts=time.time(), dedup_key=key, findings=findings or [])

    def _recover(self, watch: WatchDefinition, dedup: str) -> Alert:
        key = f"{watch.watch_id}:{dedup}"
        prev = self._open.pop(key, None)
        a = self._mk(watch, "recovery",
                     f"{watch.workload} recuperado", dedup=dedup,
                     sev="INFO")
        a.recovered = True
        if prev:
            a.findings = prev.findings
        return a

    def _dedupe(self, alerts: list[Alert]) -> list[Alert]:
        """Cooldown + dedup + group by watch (§5.5)."""
        now = time.time()
        emit: list[Alert] = []
        for a in alerts:
            last = self._last_emit.get(a.dedup_key, 0.0)
            if not a.recovered and now - last < self.cooldown_s:
                continue  # suppressed within cooldown
            self._last_emit[a.dedup_key] = now
            if not a.recovered:
                self._open[a.dedup_key] = a
            emit.append(a)
            self.history.append(a)
        return emit


class WatchRuntime:
    """Bounded local scheduler (§5.2) — thread daemon, cancellable."""

    def __init__(self, engine: AlertEngine | None = None,
                 *, max_watches: int = MAX_WATCHES) -> None:
        self.engine = engine or AlertEngine()
        self.max_watches = max_watches
        self._watches: dict[str, tuple[WatchDefinition,
                                       Callable[[], tuple[list[ExecutionSnapshot],
                                                          ExecutionSnapshot]]]] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._errors: dict[str, int] = {}

    def register(
        self, watch: WatchDefinition,
        collector: Callable[[], tuple[list[ExecutionSnapshot],
                                     ExecutionSnapshot]],
    ) -> None:
        """Register a watch with its data collector callable.

        ``collector`` returns (history, current) snapshots — injected so
        cloud collectors are an explicit caller choice (§5.3).
        """
        if len(self._watches) >= self.max_watches:
            raise ValueError(f"watch limit {self.max_watches} reached")
        if watch.interval_s < MIN_INTERVAL_S:
            raise ValueError(
                f"interval {watch.interval_s}s below min "
                f"{MIN_INTERVAL_S}s")
        self._watches[watch.watch_id] = (watch, collector)

    def unregister(self, watch_id: str) -> None:
        self._watches.pop(watch_id, None)

    def run_once(self, watch_id: str) -> list[Alert]:
        """Single bounded evaluation — also used by tests."""
        watch, collector = self._watches[watch_id]
        history, current = collector()
        return self.engine.evaluate(watch, history, current)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="sentinel-watch")
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            for wid, (watch, _c) in list(self._watches.items()):
                if not watch.enabled:
                    continue
                try:
                    self.run_once(wid)
                    self._errors.pop(wid, None)
                except Exception:
                    n = self._errors.get(wid, 0) + 1
                    self._errors[wid] = n
                    # bounded backoff — watch keeps its slot
                    self._stop.wait(min(60.0 * n, 600.0))
            # cadence: shortest configured interval (still >= min)
            interval = min(
                (w.interval_s for w, _ in self._watches.values()),
                default=MIN_INTERVAL_S)
            self._stop.wait(max(interval, MIN_INTERVAL_S))

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)


_KIND_MAP = {
    "duration_s": "duration_regression",
    "failure_rate": "job_failure",
    "retry_count": "repeated_retries",
    "cpu_utilization": "resource_saturation",
    "memory_utilization": "resource_saturation",
    "shuffle_spill_bytes": "resource_saturation",
    "throughput": "duration_regression",
    "input_bytes": "duration_regression",
    "output_bytes": "duration_regression",
    "data_freshness_s": "freshness_issue",
    "quality_score": "quality_regression",
    "iceberg_file_count": "duration_regression",
    "estimated_cost": "cost_anomaly",
}


def _kind_for(metric: str) -> str:
    return _KIND_MAP.get(metric, "duration_regression")
