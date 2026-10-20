"""Evaluation gate (ds-0037): verifies the harness runs and records
honest status even without Doctor installed."""

import os
from pathlib import Path


def test_evaluation_gate_blocked_without_env() -> None:
    os.environ.pop("DATA_SENTINEL_EVAL", None)
    os.environ.pop("DOCTOR_BIN", None)
    import importlib

    import tests.evaluation.run_evaluation as ev
    importlib.reload(ev)
    result = ev.evaluate()
    assert result["status"] == "BLOCKED"
    assert result["scenarios"] == []


def test_results_file_exists_with_real_data() -> None:
    """The committed results JSON reflects a real VERIFIED run."""
    p = Path(__file__).resolve().parents[2] / "docs" / "evaluations" / \
        "complementarity-results.json"
    assert p.exists()
    import json
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["status"] == "VERIFIED"
    assert d["totals"]["scenarios"] == 10
    assert d["totals"]["external_calls"] == 0
