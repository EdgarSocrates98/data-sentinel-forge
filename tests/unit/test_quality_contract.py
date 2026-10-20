"""Quality contract engine tests (ds-0041)."""

from pathlib import Path

import pytest

from data_sentinel.quality import (
    ContractFormatError,
    check_version_compat,
    load_contract,
    parse_contract_text,
    validate_contract,
)

VALID = """\
contract_version: "1.0"
dataset: analytics.customer_events
owner: data-eng
rules:
  - id: customer_id_not_null
    type: completeness
    column: customer_id
    expected: 1.0
    severity: high
  - id: event_unique
    type: uniqueness
    columns: [event_id]
    expected: 1.0
  - id: minimum_volume
    type: row_count
    minimum: 100000
"""


def test_parse_valid_yaml() -> None:
    c = parse_contract_text(VALID)
    assert c.contract_id == "contract"
    assert c.dataset.namespace == "analytics"
    assert c.dataset.name == "customer_events"
    assert len(c.quality_rules) == 3
    r0 = c.quality_rules[0]
    assert r0.rule_id == "customer_id_not_null"
    assert r0.target == "customer_id"
    assert r0.severity == "high"
    # columns list -> joined target
    assert c.quality_rules[1].target == "event_id"
    # extra fields preserved as parameters
    assert c.quality_rules[2].parameters["minimum"] == 100000


def test_parse_json_also_works() -> None:
    import json
    c = parse_contract_text(json.dumps({
        "contract_version": "1.0", "dataset": {"namespace": "a", "name": "b"},
        "rules": []}))
    assert c.dataset.name == "b"


def test_unknown_rule_type_rejected() -> None:
    with pytest.raises(ContractFormatError, match="desconhecido"):
        parse_contract_text(
            "dataset: a.b\nrules:\n - {id: x, type: telepathy}")


def test_malformed_yaml() -> None:
    with pytest.raises(ContractFormatError):
        parse_contract_text("{unclosed: [")
    with pytest.raises(ContractFormatError):
        parse_contract_text("- just\n- a\n- list")


def test_oversized_rejected() -> None:
    with pytest.raises(ContractFormatError, match="exceeds"):
        parse_contract_text("x: " + "y" * 1_100_000)


def test_no_eval_or_unsafe_yaml() -> None:
    """!!python/object payloads must fail safe_load."""
    with pytest.raises(ContractFormatError):
        parse_contract_text(
            "dataset: !!python/object/apply:os.system ['echo hi']")


def test_validate_detects_dup_and_bad_severity() -> None:
    c = parse_contract_text("""\
dataset: a.b
rules:
  - {id: r1, type: completeness, column: x, expected: 1.0, severity: urgent}
  - {id: r1, type: uniqueness, column: y}
""")
    v = validate_contract(c)
    msgs = " ".join(i.message for i in v.issues)
    assert "duplicado" in msgs and "severidade inválida" in msgs


def test_validate_warns_unknown_column_and_ratio() -> None:
    c = parse_contract_text("""\
dataset: a.b
schema: {real_col: long}
rules:
  - {id: r1, type: completeness, column: ghost_col, expected: 1.5}
""")
    v = validate_contract(c)
    warns = [i.message for i in v.issues if i.severity == "warning"]
    assert any("ghost_col" in w for w in warns)
    assert any("fora de [0,1]" in w for w in warns)


def test_load_contract_file(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(VALID, encoding="utf-8")
    c = load_contract(p)
    assert c.provenance == str(p)
    with pytest.raises(ContractFormatError):
        load_contract(tmp_path / "nope.yaml")


def test_version_compat() -> None:
    assert check_version_compat("1.0", "1.0").compatible
    assert check_version_compat("1.0", "1.5").compatible
    assert check_version_compat("1.0", "1.5").warnings
    assert not check_version_compat("1.0", "2.0").compatible
