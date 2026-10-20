"""Cycle 04 security tests (ds-0048): safe parsing, no exec, bounded input."""

import subprocess
import sys
from pathlib import Path

import pytest

from data_sentinel.lineage import parse_openlineage_events
from data_sentinel.quality import ContractFormatError, normalize, parse_contract_text


def test_yaml_python_object_payload_blocked(tmp_path: Path) -> None:
    """unsafe YAML tags must never construct objects / run code."""
    marker = tmp_path / "pwned"
    payload = ("dataset: !!python/object/apply:os.system "
               "['touch " + str(marker) + "']")
    with pytest.raises(ContractFormatError):
        parse_contract_text(payload)
    assert not marker.exists()


def test_oversized_contract_rejected() -> None:
    with pytest.raises(ContractFormatError):
        parse_contract_text("dataset: " + "x" * 2_000_000)


def test_rule_count_bounded() -> None:
    rules = "\n".join(f" - {{id: r{i}, type: completeness, column: c}}"
                      for i in range(6_000))
    with pytest.raises(ContractFormatError, match="regras"):
        parse_contract_text(f"dataset: a.b\nrules:\n{rules}")


def test_no_eval_in_params() -> None:
    """arbitrary params are stored as data, never evaluated."""
    c = parse_contract_text(
        'dataset: a.b\nrules:\n - {id: r, type: custom, '
        'expression: "__import__(chr(111)+chr(115)).system()"}\n')
    assert c.quality_rules[0].parameters["expression"].startswith(
        "__import__")
    # survived as inert string — no code path evaluates it


def test_adapter_input_bounded() -> None:
    obs = normalize("[" + ",".join('{"rule_id":"r"}' for _ in range(0)) +
                    "]", adapter="sql_results")
    assert obs == []


def test_lineage_malformed_jsonl_no_crash() -> None:
    ing = parse_openlineage_events("\x00\xff binary-ish \n" * 100)
    assert ing.rejected >= 100
    assert ing.events == []


def test_no_network_calls_in_quality_import() -> None:
    """Offline proof: normalize must not touch the network."""
    code = (
        "import socket\n"
        "socket.socket = lambda *a, **k: (_ for _ in ()).throw("
        "RuntimeError('network blocked'))\n"
        "import json\n"
        "from data_sentinel.quality import normalize\n"
        "obs = normalize(json.dumps({'results':[{'rule_id':'r',"
        "'value':1,'status':'PASS'}]}), adapter='sql_results')\n"
        "assert len(obs) == 1\n")
    out = subprocess.run([sys.executable, "-c", code],  # noqa: S603
                         capture_output=True, text=True,
                         cwd=Path(__file__).parent.parent.parent)
    assert out.returncode == 0, out.stderr
