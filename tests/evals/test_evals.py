"""Evaluation harness (ds-0059, §11) — deterministic, no LLM."""

import json
from pathlib import Path

from data_sentinel.agents.specialists import route

DS = json.loads((Path(__file__).parent / "agentic_evals.json")
                .read_text(encoding="utf-8"))


def test_routing_eval_precision() -> None:
    hits = 0
    for c in DS["cases"]:
        got = route(c["problem"])
        if got == c["expect_route"] or (
                c["expect_route"][0] in got):
            hits += 1
    acc = hits / len(DS["cases"])
    assert acc >= 0.8, f"routing accuracy {acc:.0%} < 80%"


def test_eval_dataset_wellformed() -> None:
    assert len(DS["cases"]) >= 5
    for c in DS["cases"]:
        assert c["id"] and c["problem"] and c["expect_route"]


def test_emr_routing_eval() -> None:
    import json
    from pathlib import Path
    ds = json.loads((Path(__file__).parent / "emr_evals.json")
                    .read_text(encoding="utf-8"))
    hits = 0
    for c in ds["cases"]:
        got = route(c["problem"])
        ok = (got and got[0] == c.get("expect_route_first")) or \
             c.get("expect_contains", "") in got
        hits += bool(ok)
    assert hits == len(ds["cases"]), f"EMR routing {hits}/{len(ds['cases'])}"
