"""Cycle 04 benchmarks (ds-0048) — real measured timings."""

import json
import random
import time
from pathlib import Path

from data_sentinel.lineage import parse_openlineage_events
from data_sentinel.lineage.graph import build_graph
from data_sentinel.quality import normalize, parse_contract_text
from data_sentinel.quality.drift import detect_drift
from data_sentinel.quality.profile import profile_column

EVIDENCE = Path("docs/evidence")


def _bench(name: str, fn, reps: int = 1) -> float:
    t0 = time.perf_counter()
    for _ in range(reps):
        fn()
    dt = (time.perf_counter() - t0) / reps
    return dt


def test_benchmarks_cycle4() -> None:
    rng = random.Random(11)  # noqa: S311
    results: dict[str, dict[str, float]] = {}

    # contract parse: 200 rules
    rules = "\n".join(
        f" - {{id: r{i}, type: completeness, column: c{i}}}"
        for i in range(200))
    contract = f'dataset: a.b\nrules:\n{rules}'
    results["contract_parse_200_rules"] = {
        "seconds": _bench("c", lambda: parse_contract_text(contract),
                          reps=20)}

    # adapter normalize: 5k rows
    rows = [{"rule_id": f"r{i}", "value": i, "expected": 0,
             "status": "PASS"} for i in range(5000)]
    payload = json.dumps({"results": rows})
    results["adapter_normalize_5k_rows"] = {
        "seconds": _bench("a", lambda: normalize(payload,
                                               adapter="sql_results"),
                          reps=10)}

    # profiling: 50k values
    vals = [rng.gauss(100, 15) for _ in range(50_000)]
    results["profile_column_50k"] = {
        "seconds": _bench("p", lambda: profile_column("v", vals), reps=5)}

    # drift: 2x 10k samples
    base = [rng.gauss(0, 1) for _ in range(10_000)]
    cur = [rng.gauss(0.3, 1) for _ in range(10_000)]
    results["drift_10k_vs_10k"] = {
        "seconds": _bench("d", lambda: detect_drift("x", base, cur),
                          reps=10)}

    # lineage: 1k events -> graph
    evs = "\n".join(
        json.dumps({"eventType": "COMPLETE",
                    "run": {"runId": f"r{i}"},
                    "job": {"name": f"job{i % 100}"},
                    "inputs": [{"namespace": "ns",
                                "name": f"ds{i % 50}"}],
                    "outputs": [{"namespace": "ns",
                                 "name": f"ds{(i + 1) % 50}"}]})
        for i in range(1000))
    def _lineage() -> None:
        build_graph(parse_openlineage_events(evs).events)
    results["lineage_1k_events_graph"] = {
        "seconds": _bench("l", _lineage, reps=5)}

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / "benchmarks-cycle4.json"
    existing = json.loads(out.read_text()) if out.exists() else {}
    existing.update(results)
    out.write_text(json.dumps(existing, indent=2, sort_keys=True))
    for k, v in results.items():
        assert v["seconds"] < 30, f"{k} too slow: {v['seconds']:.3f}s"
