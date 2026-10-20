"""ds-0094 — pytest entry for the Cycle 08 eval harness.

Runs the real harness (all 30 golden scenarios via the golden runner)
and asserts the measured output is structurally honest. Regenerates
docs/evaluations/cycle8-results.json as a side effect — the committed
file is always produced by an actual run.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = (Path(__file__).resolve().parents[2] / "docs" / "evaluations"
       / "cycle8-results.json")


def test_cycle8_eval_measured() -> None:
    from tests.evaluation import run_cycle8_eval as ev

    result = ev.run()
    assert result["status"] == "VERIFIED"
    assert result["git_sha"] != "unknown"
    t = result["totals"]
    assert t["scenarios"] == 30
    assert t["external_calls"] == 0
    # every scenario accounted for exactly once (verdicts are mutually
    # exclusive; finding-level tp/fp extras are counted separately)
    verdicts = {r["verdict"] for r in result["scenarios"]}
    assert verdicts <= {"tp", "fp", "fn", "tn", "delegated"}
    assert len({r["scenario_id"] for r in result["scenarios"]}) == 30
    # latency really measured for every scenario
    for r in result["scenarios"]:
        assert r["latency_ms"] >= 0 and r["verdict"] in {
            "tp", "fp", "fn", "tn", "delegated"}
    assert OUT.exists()
    on_disk = json.loads(OUT.read_text(encoding="utf-8"))
    assert on_disk["totals"] == t
