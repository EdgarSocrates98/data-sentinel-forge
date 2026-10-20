"""Run comparison engine — comparability gate + deltas (§3.4, §3.5).

Hard rule (§3.4): snapshots with different workloads are NEVER
treated as a controlled comparison.
"""

from __future__ import annotations

from statistics import median

from data_sentinel.core.contracts.snapshot import (
    BaselineKind,
    ComparisonResult,
    ExecutionSnapshot,
)


def check_comparable(
    a: ExecutionSnapshot, b: ExecutionSnapshot,
) -> list[str]:
    """Reasons two snapshots cannot be compared (§3.4)."""
    reasons: list[str] = []
    if a.platform != b.platform:
        reasons.append(f"platform differs: {a.platform} vs {b.platform}")
    if a.job_id and b.job_id and a.job_id != b.job_id:
        reasons.append(f"different jobs: {a.job_id} vs {b.job_id}")
    if a.runtime and b.runtime and a.runtime != b.runtime:
        reasons.append(f"runtime differs: {a.runtime} vs {b.runtime}")
    fp_a, fp_b = a.config_fingerprint, b.config_fingerprint
    if fp_a and fp_b and fp_a != fp_b:
        reasons.append("configuration fingerprint differs")
    if (a.input_bytes is not None and b.input_bytes is not None
            and a.input_bytes > 0 and b.input_bytes > 0):
        ratio = max(a.input_bytes, b.input_bytes) / \
            min(a.input_bytes, b.input_bytes)
        if ratio > 10:
            reasons.append(
                f"input volume differs {ratio:.1f}x — different workload")
    for m in ("duration_s",):
        if getattr(a, m) is None or getattr(b, m) is None:
            reasons.append(f"metric unavailable: {m}")
    return reasons


def select_baseline(
    snapshots: list[ExecutionSnapshot],
    sel: BaselineKind,
) -> list[ExecutionSnapshot]:
    """Resolve a baseline set (§3.3) — deterministic, sorted by time."""
    snaps = sorted(snapshots, key=lambda s: s.started_at or "")
    if sel.kind == "previous":
        return snaps[-1:] if snaps else []
    if sel.kind == "rolling":
        w = sel.window or 5
        return snaps[-w:]
    if sel.kind == "median":
        return snaps  # median computed over all
    if sel.kind == "reference":
        return [s for s in snaps if s.run_id == sel.reference_run_id]
    if sel.kind == "cohort":
        return snaps
    return []


def _median_duration(snaps: list[ExecutionSnapshot]) -> float | None:
    ds = [s.duration_s for s in snaps if s.duration_s is not None]
    return median(ds) if ds else None


def compare_snapshots(
    current: ExecutionSnapshot,
    baseline: list[ExecutionSnapshot],
) -> ComparisonResult:
    """Compare *current* to a baseline set — honest deltas only."""
    res = ComparisonResult(comparable=True)
    for b in baseline:
        res.incomparability_reasons.extend(check_comparable(current, b))
    res.incomparability_reasons = sorted(set(res.incomparability_reasons))
    if res.incomparability_reasons or not baseline:
        res.comparable = False
        if not baseline:
            res.incomparability_reasons.append("no baseline snapshots")
            res.limitations.append(
                "sem baseline — nenhuma comparação controlada afirmada")
        return res

    base_dur = _median_duration(baseline)
    if current.duration_s is not None and base_dur is not None:
        res.duration_delta_s = current.duration_s - base_dur
        if base_dur > 0:
            res.duration_delta_pct = (
                res.duration_delta_s / base_dur) * 100.0
    else:
        res.limitations.append(
            "duração indisponível no baseline ou no snapshot atual")

    keys = {k for b in baseline for k in b.resource_metrics}
    for k in sorted(keys):
        cur = current.resource_metrics.get(k)
        base_vals = [b.resource_metrics[k] for b in baseline
                     if k in b.resource_metrics]
        if cur is None or not base_vals:
            res.limitations.append(f"métrica ausente: {k}")
            continue
        res.resource_deltas[k] = cur - median(base_vals)

    if current.input_bytes is not None:
        base_in = [b.input_bytes for b in baseline
                   if b.input_bytes is not None]
        if base_in:
            res.volume_delta_input = current.input_bytes - int(
                median(base_in))
    if current.output_bytes is not None:
        base_out = [b.output_bytes for b in baseline
                    if b.output_bytes is not None]
        if base_out:
            res.volume_delta_output = current.output_bytes - int(
                median(base_out))

    base_failures = [b.failure for b in baseline if b.failure is not None]
    if current.failure is not None and base_failures:
        prev_failed = any(base_failures)
        res.failure_regression = bool(current.failure and not prev_failed)
    else:
        res.limitations.append(
            "status de falha desconhecido — regressão de falha "
            "não avaliada")

    for b in baseline:
        if (b.config_fingerprint and current.config_fingerprint
                and b.config_fingerprint != current.config_fingerprint):
            res.config_drift.append(
                f"config fingerprint mudou vs run {b.run_id}")

    for k in sorted({k for b in baseline for k in b.cost_observations}
                    | set(current.cost_observations)):
        cur = current.cost_observations.get(k)
        base = [b.cost_observations[k] for b in baseline
                if k in b.cost_observations]
        if cur is not None and base:
            res.cost_delta[k] = cur - median(base)
    return res
