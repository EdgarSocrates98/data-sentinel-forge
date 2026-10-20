"""Profiling + drift tests (ds-0043)."""

import random

from data_sentinel.core.contracts import DriftLevel
from data_sentinel.quality import drift as drift_mod
from data_sentinel.quality.drift import (
    detect_categorical_drift,
    detect_drift,
    drift_findings,
    psi,
)
from data_sentinel.quality.profile import profile_column, profile_table


def test_profile_numeric() -> None:
    p = profile_column("amount", [1.0, 2.0, 3.0, 4.0, None, 5.0])
    assert p.count == 6 and p.null_count == 1
    assert p.dtype_inferred == "numeric"
    assert p.mean == 3.0
    assert p.min_value == 1.0 and p.max_value == 5.0
    assert p.engine in ("numpy", "stdlib")


def test_profile_categorical() -> None:
    p = profile_column("status", ["ok", "ok", "bad", "ok"])
    assert p.dtype_inferred != "numeric"
    assert p.top_values["ok"] == 3
    assert p.distinct_count == 2


def test_profile_table() -> None:
    rows = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    profs = profile_table(rows)
    assert set(profs) == {"a", "b"}
    assert profs["a"].dtype_inferred == "numeric"


def test_psi_identical_is_zero() -> None:
    rng = random.Random(0)  # noqa: S311
    a = [rng.gauss(0, 1) for _ in range(200)]
    assert abs(psi(a, a)) < 1e-9


def test_drift_insufficient() -> None:
    r = detect_drift("x", [1, 2], [1, 2])
    assert r.level == DriftLevel.UNKNOWN
    assert r.confidence == "UNKNOWN"


def test_drift_detects_shift() -> None:
    rng = random.Random(1)  # noqa: S311
    base = [rng.gauss(0, 1) for _ in range(300)]
    cur = [rng.gauss(3, 1) for _ in range(300)]
    r = detect_drift("amount", base, cur)
    assert r.level in (DriftLevel.MEDIUM, DriftLevel.HIGH)
    assert r.evidence
    assert r.engine in ("scipy", "heuristic")


def test_drift_stable() -> None:
    rng = random.Random(2)  # noqa: S311
    base = [rng.gauss(0, 1) for _ in range(300)]
    cur = [rng.gauss(0.02, 1) for _ in range(300)]
    r = detect_drift("x", base, cur)
    assert r.level in (DriftLevel.NONE, DriftLevel.LOW)


def test_categorical_drift() -> None:
    r = detect_categorical_drift("status",
                                 {"ok": 90, "bad": 10},
                                 {"ok": 30, "bad": 70})
    assert r.level != DriftLevel.NONE


def test_drift_findings_only_nonzero() -> None:
    rng = random.Random(3)  # noqa: S311
    base = [rng.gauss(0, 1) for _ in range(300)]
    cur = [rng.gauss(5, 1) for _ in range(300)]
    res = [detect_drift("amount", base, cur),
           detect_drift("stable", base, base)]
    fs, evs = drift_findings(res)
    assert len(fs) == 1
    assert "amount" in fs[0].explanation
    assert fs[0].status.value in ("CONFIRMED", "PROBABLE")
    assert len(evs) == 1
    assert fs[0].evidence_ids == [evs[0].evidence_id]  # resolves — §4


def test_engine_declared() -> None:
    r = detect_drift("x", list(range(100)), list(range(100, 200)))
    if drift_mod._HAS_SCIPY:
        assert r.engine == "scipy"
    else:
        assert r.engine == "heuristic"
        assert r.limitations
