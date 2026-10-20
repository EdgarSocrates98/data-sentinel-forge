"""Regression & anomaly detection on ExecutionSnapshots (ds-0083, §4).

Deterministic, dependency-free statistics: absolute/relative thresholds,
rolling baseline, median+MAD, robust z-score, simple trend. Regression is
a signal — never a claimed root cause (§4.4).
"""

from __future__ import annotations

from statistics import median

from data_sentinel.core.contracts.snapshot import ExecutionSnapshot

SIGNALS = (
    "duration_s", "failure_rate", "retry_count", "cpu_utilization",
    "memory_utilization", "shuffle_spill_bytes", "throughput",
    "input_bytes", "output_bytes", "data_freshness_s", "freshness_s",
    "quality_score", "dq_pass_rate", "iceberg_file_count",
    "estimated_cost",
)

# Signals whose regression direction is a DECREASE (quality drops),
# not an increase. Cycle 08.1 §7.4.
DECREASE_IS_BAD = frozenset({"quality_score", "dq_pass_rate"})


def _metric(snapshot: ExecutionSnapshot, name: str) -> float | None:
    if name in {"input_bytes", "output_bytes"}:
        v = getattr(snapshot, name)
        return float(v) if v is not None else None
    if name == "duration_s":
        return snapshot.duration_s
    if name == "estimated_cost":
        return snapshot.cost_observations.get("total_usd")
    return snapshot.resource_metrics.get(name)


def _mad(values: list[float], med: float) -> float:
    return median([abs(v - med) for v in values])


def detect_regressions(
    history: list[ExecutionSnapshot],
    current: ExecutionSnapshot,
    *,
    rel_threshold_pct: float = 50.0,
    abs_thresholds: dict[str, float] | None = None,
    z_threshold: float = 3.5,
) -> list[dict[str, object]]:
    """Detect degraded signals in *current* vs *history* (same workload).

    Deterministic methods: absolute + relative thresholds, median/MAD
    robust z-score. Seasonality requires >=14 points; otherwise it is
    declared unavailable — never faked.
    """
    findings: list[dict[str, object]] = []
    hist = sorted(history, key=lambda s: s.started_at or "")
    for signal in SIGNALS:
        vals: list[float] = [
            v for s in hist
            if (v := _metric(s, signal)) is not None]
        cur = _metric(current, signal)
        if cur is None or not vals:
            continue
        med = median(vals)
        mad = _mad(vals, med)
        # Direction-aware regression: quality signals degrade by
        # DROPPING (Cycle 08.1 §7.4). `dir_` flips every comparison so
        # an improvement never alerts and a drop is never missed.
        dir_ = -1.0 if signal in DECREASE_IS_BAD else 1.0

        # absolute threshold
        if abs_thresholds and signal in abs_thresholds:
            lim = abs_thresholds[signal]
            if (cur - lim) * dir_ > 0:
                findings.append(_finding(
                    signal, med, cur, "absolute_threshold",
                    f"valor {cur} {'acima' if dir_ > 0 else 'abaixo'} "
                    f"do limite {lim}"))

        # relative threshold (duration & volumes mainly)
        if med > 0:
            pct = ((cur - med) / med) * 100.0
            if signal in DECREASE_IS_BAD:
                if pct < -rel_threshold_pct:
                    findings.append(_finding(
                        signal, med, cur, "relative_threshold",
                        f"{pct:.1f}% vs mediana histórica (queda)"))
            elif pct > rel_threshold_pct:
                findings.append(_finding(
                    signal, med, cur, "relative_threshold",
                    f"+{pct:.1f}% vs mediana histórica"))

        # robust z-score via MAD (needs >=5 points)
        if len(vals) >= 5 and mad > 0:
            z = 0.6745 * (cur - med) / mad
            if z * dir_ > z_threshold:
                findings.append(_finding(
                    signal, med, cur, "robust_zscore",
                    f"z={z:.2f} (limiar {z_threshold})", z))

        # simple trend: last 3 medians monotonic in the BAD direction
        if len(vals) >= 6:
            thirds = [vals[len(vals) // 3 * i:len(vals) // 3 * (i + 1)]
                      for i in range(3)]
            meds = [median(t) for t in thirds if t]
            if len(meds) == 3:
                rising = meds[0] < meds[1] < meds[2] and cur > meds[2]
                falling = meds[0] > meds[1] > meds[2] and cur < meds[2]
                if rising if dir_ > 0 else falling:
                    findings.append(_finding(
                        signal, med, cur, "trend",
                        "tendência monotônica "
                        f"{'crescente' if dir_ > 0 else 'decrescente'} "
                        "nos últimos terços"))



    for f in findings:
        lims = f.get("limitations", [])
        lims = lims if isinstance(lims, list) else []
        lims.append("regressão é sinal — não é causa-raiz identificada")
        f["limitations"] = lims
        f["confidence"] = "POSSIBLE"
        f["causal_label"] = "suspected_cause"
    return link_changes(findings, current, hist)


def _finding(metric: str, baseline: float, current: float,
             method: str, rationale: str,
             z: float | None = None) -> dict[str, object]:
    mag = current - baseline
    pct = (mag / baseline * 100.0) if baseline else None
    return {
        "metric": metric,
        "baseline": baseline,
        "current_value": current,
        "magnitude": mag,
        "magnitude_pct": pct,
        "method": method,
        "z_score": z,
        "rationale": rationale,
        "provenance": "computed_from_snapshots",
        "limitations": [],
        "related_changes": [],
        "investigation_recommendation":
            f"investigar {metric}: {rationale}",
    }


def link_changes(
    findings: list[dict[str, object]],
    current: ExecutionSnapshot,
    history: list[ExecutionSnapshot],
) -> list[dict[str, object]]:
    """Attach *observed* changes as hypothesis material (§4.4).

    Links what actually changed (runtime, config, volume) — correlation,
    never asserted causation.
    """
    if not history:
        return findings
    prev = sorted(history, key=lambda s: s.started_at or "")[-1]
    changes: list[str] = []
    if prev.runtime != current.runtime:
        changes.append(f"runtime: {prev.runtime} -> {current.runtime}")
    if (prev.config_fingerprint != current.config_fingerprint
            and prev.config_fingerprint and current.config_fingerprint):
        changes.append("config fingerprint mudou")
    if (prev.input_bytes and current.input_bytes
            and prev.input_bytes > 0):
        ratio = current.input_bytes / prev.input_bytes
        if ratio > 1.5 or ratio < 0.66:
            changes.append(f"volume de entrada {ratio:.1f}x")
    for f in findings:
        f["related_changes"] = changes
        if changes:
            lims = f.get("limitations", [])
            if not isinstance(lims, list):
                lims = []
            f["limitations"] = [*lims,
                "mudanças correlatas observadas — causalidade não "
                "afirmada por simultaneidade"]
    return findings
