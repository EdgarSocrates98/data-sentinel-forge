"""Tests for ds-0016 — Spark configuration advisor."""

from pathlib import Path

from data_sentinel.analyzers.spark.config import SparkConfigAdvisor, parse_config_text
from data_sentinel.analyzers.spark.config.matrix import CONFIG_MATRIX, support_status
from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    ExecutionContext,
    FindingStatus,
    Platform,
    SourceType,
)
from data_sentinel.core.security import InputFile

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "config"


def _load(name: str) -> InputFile:
    p = FIXTURES / name
    return InputFile(path=str(p), text=p.read_text(encoding="utf-8"), size_bytes=p.stat().st_size)


def _request(**extra: object) -> DiagnosticRequest:
    ctx = ExecutionContext(extra=dict(extra)) if extra else None
    return DiagnosticRequest(
        source_type=SourceType.CONFIG,
        artifact_references=[ArtifactReference(uri="file://fixture")],
        platform=Platform.SPARK,
        execution_context=ctx,
    )


def _analyze(name: str, **extra: object):
    return SparkConfigAdvisor().analyze(_request(**extra), [_load(name)])


class TestParsers:
    def test_properties(self) -> None:
        entries = parse_config_text("a.b=1\nc.d = 2\n# comment")
        assert {(e.key, e.value, e.provenance) for e in entries} == {
            ("a.b", "1", "properties_file"),
            ("c.d", "2", "properties_file"),
        }

    def test_conf_frag(self) -> None:
        entries = parse_config_text("--conf x.y=z --conf a.b=c")
        assert {(e.key, e.value) for e in entries} == {("x.y", "z"), ("a.b", "c")}
        assert all(e.provenance == "conf_fragment" for e in entries)


class TestMatrix:
    def test_all_11_configs_present(self) -> None:
        expected = {
            "spark.sql.adaptive.enabled",
            "spark.sql.shuffle.partitions",
            "spark.sql.autoBroadcastJoinThreshold",
            "spark.sql.adaptive.coalescePartitions.enabled",
            "spark.sql.adaptive.skewJoin.enabled",
            "spark.sql.files.maxPartitionBytes",
            "spark.executor.memory",
            "spark.executor.cores",
            "spark.driver.memory",
            "spark.dynamicAllocation.enabled",
            "spark.sql.cbo.enabled",
        }
        assert expected <= set(CONFIG_MATRIX)

    def test_glue30_aqe_unsupported(self) -> None:
        status, _ = support_status("spark.sql.adaptive.enabled", None, "3.0")
        assert status == "unsupported"

    def test_unknown_config(self) -> None:
        status, _ = support_status("custom.x", "3.4", None)
        assert status == "not_in_matrix"

    def test_unknown_runtime(self) -> None:
        status, _ = support_status("spark.sql.shuffle.partitions", None, None)
        assert status == "unknown_runtime"


class TestAdvisor:
    def test_aqe_disabled_flagged(self) -> None:
        result = _analyze("spark_props.properties", spark_version="3.4")
        assert any(
            "AQE desabilitado" in f.explanation for f in result.findings
        )

    def test_incompatible_config_glue3(self) -> None:
        result = _analyze("glue3_incompatible.properties", glue_version="3.0")
        incompat = [f for f in result.findings if "incompatível" in f.explanation]
        assert incompat and incompat[0].status == FindingStatus.CONFIRMED

    def test_broadcast_memory_pressure(self) -> None:
        result = _analyze("conf_frag.txt", spark_version="3.4")
        hit = next(
            f for f in result.findings if "autoBroadcastJoinThreshold" in f.explanation
        )
        assert hit.status == FindingStatus.POSSIBLE
        assert "custo" in hit.explanation or "quota" in hit.explanation

    def test_oom_signal_strengthens(self) -> None:
        result = _analyze(
            "spark_props.properties",
            spark_version="3.4",
            workload_oom_evidence="true",
        )
        hit = next(
            f for f in result.findings if "executor.memory" in f.explanation
        )
        assert hit.status == FindingStatus.PROBABLE
        assert "custo" in hit.explanation

    def test_cbo_without_stats(self) -> None:
        result = _analyze("cbo_no_stats.properties", spark_version="3.5")
        assert any("CBO" in f.explanation for f in result.findings)

    def test_missing_runtime_unknown(self) -> None:
        result = _analyze("spark_props.properties")
        assert any(
            f.status == FindingStatus.UNKNOWN and "Runtime" in f.explanation
            for f in result.findings
        )

    def test_glue_args_provenance(self) -> None:
        result = _analyze("glue_args.json", glue_version="4.0")
        provs = {
            v["provenance"] for v in result.metadata["configs"].values()
        }
        assert "glue_arguments" in provs

    def test_recommendation_structure(self) -> None:
        result = _analyze("spark_props.properties", spark_version="3.4")
        recs = result.metadata["recommendations"]
        assert recs
        r = recs[0]
        assert r["target"] and r["proposed_change"] and r["rationale"]
        assert "hipótese" in r["expected_effect"]
        assert r["rollback_plan"] and r["validation_plan"]

    def test_no_universal_recommendations(self) -> None:
        # Glue 3.0 (no AQE) + aqe config — no "enable AQE" recommendation
        result = _analyze("glue3_incompatible.properties", glue_version="3.0")
        assert not any(
            r["recommendation_id"] == "rec-aqe-enable"
            for r in result.metadata["recommendations"]
        )

    def test_empty_config_unknown(self) -> None:
        empty = InputFile(path="empty.properties", text="", size_bytes=0)
        result = SparkConfigAdvisor().analyze(_request(), [empty])
        assert any(f.status == FindingStatus.UNKNOWN for f in result.findings)
