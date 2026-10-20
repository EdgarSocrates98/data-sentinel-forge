"""Quality adapter tests (ds-0042)."""

import json
from pathlib import Path

from data_sentinel.core.contracts import ObservationStatus
from data_sentinel.quality import (
    detect_adapter,
    list_adapters,
    normalize,
    parse_ge,
    parse_pydeequ,
)

FIX = Path(__file__).parent.parent / "fixtures" / "quality"


def test_pydeequ_metrics() -> None:
    data = json.loads((FIX / "pydeequ_metrics.json").read_text())
    obs = parse_pydeequ(data, source="test")
    assert len(obs) == 4
    assert obs[0].observed_value == 0.97
    assert obs[0].source == "pydeequ"
    assert obs[0].status == ObservationStatus.PASS
    # analyzer failure -> UNKNOWN, never PASS
    err = next(o for o in obs if o.rule_id == "amount")
    assert err.status == ObservationStatus.UNKNOWN
    assert "analyzer falhou" in err.limitations[-1]


def test_ge_results() -> None:
    data = json.loads((FIX / "ge_result.json").read_text())
    obs = parse_ge(data)
    assert len(obs) == 2
    assert obs[0].status == ObservationStatus.PASS
    assert obs[1].status == ObservationStatus.FAIL
    assert obs[0].metric_name == "expect_column_values_to_not_be_null"
    assert obs[0].run_id == "nightly-2026-03"


def test_sql_rows() -> None:
    text = (FIX / "sql_results.json").read_text()
    obs = normalize(text, adapter="sql_results")
    assert len(obs) == 2
    assert obs[0].status == ObservationStatus.PASS
    assert obs[1].status == ObservationStatus.FAIL
    assert obs[1].unit == "hours"
    assert obs[0].run_id == "job-7"


def test_deequ_checks_autodetect() -> None:
    text = (FIX / "deequ_checks.json").read_text()
    data = json.loads(text)
    assert detect_adapter(data) == "deequ_checks"
    obs = normalize(text)
    assert len(obs) == 2
    assert obs[0].status == ObservationStatus.PASS
    assert obs[1].status == ObservationStatus.FAIL


def test_detect_ge() -> None:
    data = json.loads((FIX / "ge_result.json").read_text())
    assert detect_adapter(data) == "great_expectations"


def test_missing_value_never_pass() -> None:
    obs = parse_pydeequ({"metrics": [
        {"instance": "x", "name": "Completeness"}]})
    assert obs[0].status == ObservationStatus.UNKNOWN
    assert obs[0].observed_value is None


def test_adapter_descriptors() -> None:
    descs = list_adapters()
    names = {d.name for d in descs}
    assert {"pydeequ", "great_expectations", "sql_results",
            "dataframe_export", "deequ_checks"} <= names
    for d in descs:
        assert d.version and d.input_format and d.limitations


def test_malformed_returns_empty() -> None:
    assert normalize("not structured at all {{{") == []
    assert normalize("42") == []
