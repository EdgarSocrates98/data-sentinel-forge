"""Evaluation harness (ds-0059, §11) — deterministic, no LLM."""

import json
from pathlib import Path

from data_sentinel.agents.specialists import route

DS = json.loads((Path(__file__).parent / "agentic_evals.json")
                .read_text())


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
