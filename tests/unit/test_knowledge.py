"""ds-0022 — knowledge base: schema, engine, packaging."""

import subprocess
import sys
import tempfile
import venv
from pathlib import Path

import pytest

from data_sentinel.core.contracts.enums import SupportStatus
from data_sentinel.knowledge import (
    Rule,
    load_packaged_rules,
    load_rules,
    select,
    validate_rule,
)

VALID = """
rule_id: test-rule
version: "1.0.0"
service: aws_glue
engine: spark
runtime: glue-5.1
status: SUPPORTED
references: ["https://example.com/doc"]
last_verified: "2026-01-01"
owner: team
reviewer: rev
history: []
"""


class TestSchemaValidation:
    def test_valid_rule_loads(self):
        rules, errors = load_rules([("t.yaml", VALID)])
        assert errors == []
        assert rules[0].rule_id == "test-rule"
        assert rules[0].status == SupportStatus.SUPPORTED

    @pytest.mark.parametrize(
        "missing",
        ["rule_id", "service", "status", "references", "last_verified", "owner"],
    )
    def test_missing_required_fields(self, missing):
        import yaml

        raw = yaml.safe_load(VALID)
        del raw[missing]
        errors = validate_rule(raw, source="t.yaml")
        assert any(missing in e for e in errors)

    def test_invalid_status_rejected(self):
        import yaml

        raw = yaml.safe_load(VALID)
        raw["status"] = "MAYBE_WORKS"
        assert validate_rule(raw, source="t.yaml")

    def test_rule_without_references_rejected(self):
        import yaml

        raw = yaml.safe_load(VALID)
        raw["references"] = []
        assert any("fonte" in e for e in validate_rule(raw, source="t.yaml"))

    def test_invalid_yaml_document(self):
        rules, errors = load_rules([("bad.yaml", "{{{")])
        assert rules == []
        assert errors

    def test_duplicate_rule_id_flagged(self):
        _, errors = load_rules([("a.yaml", VALID), ("b.yaml", VALID)])
        assert any("duplicado" in e for e in errors)


class TestEngine:
    def _rule(self, **kw):
        base = {
            "rule_id": kw.pop("rule_id", "r"),
            "version": "1.0.0",
            "service": kw.pop("service", "aws_glue"),
            "status": kw.pop("status", SupportStatus.SUPPORTED),
            "references": ["x"],
            "last_verified": "d",
            "owner": "o",
            "reviewer": "r",
        }
        return Rule(**{**base, **kw})

    def test_specific_beats_generic(self):
        generic = self._rule(rule_id="gen")
        specific = self._rule(rule_id="spec", runtime="glue-5.1")
        ctx = {"service": "aws_glue", "runtime": "glue-5.1"}
        assert select([generic, specific], ctx).rule.rule_id == "spec"

    def test_no_match_unknown_fallback(self):
        r = self._rule(runtime="glue-5.1")
        m = select([r], {"service": "aws_glue", "runtime": "glue-4.0"})
        assert m.status == SupportStatus.UNKNOWN
        assert m.rule is None

    def test_tie_is_conflict_not_silent(self):
        a = self._rule(rule_id="a", runtime="glue-5.1")
        b = self._rule(rule_id="b", runtime="glue-5.1", status=SupportStatus.UNSUPPORTED)
        m = select([a, b], {"service": "aws_glue", "runtime": "glue-5.1"})
        assert m.status == SupportStatus.UNKNOWN
        assert m.conflicts and set(m.candidates) == {"a", "b"}

    def test_wildcard_matches(self):
        r = self._rule(operation="*")
        assert r.matches({"service": "aws_glue", "operation": "merge"})

    def test_conditions_must_match(self):
        r = self._rule(conditions={"account_mode": "cross"})
        assert not r.matches({"service": "aws_glue", "account_mode": "same"})
        assert r.matches({"service": "aws_glue", "account_mode": "cross"})

    def test_different_statuses_preserved(self):
        r = self._rule(status=SupportStatus.SUPPORTED_WITH_CONSTRAINTS)
        m = select([r], {"service": "aws_glue"})
        assert m.status == SupportStatus.SUPPORTED_WITH_CONSTRAINTS


class TestPackagedRules:
    def test_packaged_rules_load_without_errors(self):
        rules, errors = load_packaged_rules()
        assert errors == []
        assert len(rules) >= 7  # 5 runtime + 2 fgac mínimos

    def test_packaged_rules_cover_runtime_matrix(self):
        rules, _ = load_packaged_rules()
        ctx = {"service": "aws_glue", "engine": "spark", "runtime": "glue-5.1",
               "table_format": "iceberg"}
        m = select(rules, ctx)
        assert m.status == SupportStatus.SUPPORTED

    def test_v3_never_generalized(self):
        rules, _ = load_packaged_rules()
        # v3 em glue-4.0 → UNSUPPORTED; em glue-5.1 → NOT_VERIFIED (não SUPPORTED)
        c4 = {"service": "aws_glue", "engine": "spark",
              "runtime": "glue-4.0", "table_format": "iceberg-v3"}
        c51 = {"service": "aws_glue", "engine": "spark",
               "runtime": "glue-5.1", "table_format": "iceberg-v3"}
        assert select(rules, c4).status == SupportStatus.UNSUPPORTED
        assert select(rules, c51).status == SupportStatus.NOT_VERIFIED

    def test_every_rule_has_provenance(self):
        rules, _ = load_packaged_rules()
        for r in rules:
            assert r.references and r.last_verified and r.owner and r.reviewer


@pytest.mark.slow
def test_wheel_contains_rules_and_loads_outside_checkout():
    """§8.4: wheel instalado em venv limpa carrega as regras — sem checkout."""
    wheel = next(Path("dist").glob("data_sentinel-*.whl"))
    with tempfile.TemporaryDirectory() as td:
        venv.create(td, with_pip=True)
        scripts = "Scripts" if sys.platform == "win32" else "bin"
        pip = Path(td) / scripts / "pip"
        subprocess.run(  # noqa: S603 - wheel local construído pelo próprio teste
            [str(pip), "install", "-q", str(wheel.resolve())],
            check=True, capture_output=True,
        )
        code = (
            "from data_sentinel.knowledge import load_packaged_rules;"
            "rules, errors = load_packaged_rules();"
            "assert errors == [], errors;"
            "assert len(rules) >= 7;"
            "print(len(rules))"
        )
        out = subprocess.run(  # noqa: S603 - python da venv criada pelo teste
            [str(Path(td) / scripts / "python"), "-c", code],
            check=True, capture_output=True, text=True, cwd=td,
        )
        assert int(out.stdout.strip()) >= 7
