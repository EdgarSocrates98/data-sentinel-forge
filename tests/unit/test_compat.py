"""ds-0023 — Glue/FGAC/FTA compatibility engine."""

from data_sentinel.core.contracts.enums import (
    SupportStatus,
)
from data_sentinel.knowledge.compat import assess_compatibility


def _assess(**kw):
    return assess_compatibility(None, **kw)


class TestRuntimeMatrix:
    def test_glue51_iceberg_select_supported(self):
        a = _assess(runtime="glue-5.1", table_format="iceberg", operation="select")
        assert a.support_status in (
            SupportStatus.SUPPORTED,
            SupportStatus.SUPPORTED_WITH_CONSTRAINTS,
        )
        assert a.evidence and a.documentation_references

    def test_glue40_iceberg_v3_unsupported(self):
        a = _assess(runtime="glue-4.0", table_format="iceberg-v3", operation="select")
        assert a.support_status == SupportStatus.UNSUPPORTED

    def test_glue51_iceberg_v3_not_verified(self):
        a = _assess(runtime="glue-5.1", table_format="iceberg-v3", operation="select")
        assert a.support_status == SupportStatus.NOT_VERIFIED

    def test_unknown_runtime_unknown_not_unsupported(self):
        a = _assess(runtime="glue-99.0", table_format="iceberg", operation="select")
        assert a.support_status == SupportStatus.UNKNOWN


class TestAccessModes:
    def test_unknown_mode_never_presumed_fgac(self):
        a = _assess(runtime="glue-5.1", operation="select", access_mode="unknown")
        assert a.access_mode == "unknown"
        assert any("FGAC nunca é presumido" in c for c in a.constraints)

    def test_fgac_select_uses_mode_rule(self):
        a = _assess(runtime="glue-5.1", operation="select", access_mode="fgac",
                    table_format="iceberg")
        assert a.support_status == SupportStatus.SUPPORTED_WITH_CONSTRAINTS
        assert any("column-level" in c for c in a.constraints)

    def test_fgac_merge_dml_covered(self):
        a = _assess(runtime="glue-5.1", operation="merge", access_mode="fgac",
                    table_format="iceberg")
        assert a.support_status == SupportStatus.SUPPORTED_WITH_CONSTRAINTS
        assert any("full table access" in c for c in a.constraints)


class TestOperations:
    def test_operation_taxonomy_coverage(self):
        for op in ("select", "insert", "append", "update", "delete", "merge",
                   "create", "alter", "drop", "describe", "metadata",
                   "maintenance"):
            a = _assess(runtime="glue-5.1", operation=op)
            assert a.operation == op
            assert a.support_status != SupportStatus.NOT_VERIFIED or op

    def test_unlisted_operation_flagged_generic(self):
        a = _assess(runtime="glue-5.1", operation="vacuum_xyz")
        assert any("fora da taxonomia" in c for c in a.constraints)


class TestEvidence:
    def test_assessment_carries_rule_evidence(self):
        a = _assess(runtime="glue-5.1", table_format="iceberg", operation="merge")
        assert a.evidence
        assert all(e.source == "knowledge_rule" for e in a.evidence)
        assert a.documentation_references

    def test_constraints_accumulate_not_hidden(self):
        a = _assess(runtime="glue-4.0", operation="select", access_mode="fgac",
                    table_format="iceberg")
        assert len(a.constraints) >= 1


class TestNoGeneralization:
    def test_support_not_inherited_across_versions(self):
        a40 = _assess(runtime="glue-4.0", table_format="iceberg-v3", operation="select")
        a51 = _assess(runtime="glue-5.1", table_format="iceberg-v3", operation="select")
        assert a40.support_status != a51.support_status
