"""ds-0021 — Iceberg metadata intelligence."""

from pathlib import Path

import pytest

from data_sentinel.analyzers.iceberg import (
    MetadataParseError,
    parse_metadata,
)
from data_sentinel.analyzers.protocol import InputFile
from data_sentinel.analyzers.registry import registry
from data_sentinel.core.contracts.entities import (
    ArtifactReference,
    DiagnosticRequest,
)
from data_sentinel.core.contracts.enums import (
    FindingCategory,
    FindingStatus,
    Platform,
    SourceType,
)

FX = Path("fixtures/iceberg")


def _req() -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=SourceType.ICEBERG_METADATA,
        artifact_references=[ArtifactReference(uri="file://iceberg")],
        platform=Platform.AWS_GLUE,
    )


def _inp(name: str) -> InputFile:
    p = FX / name
    t = p.read_text(encoding="utf-8")
    return InputFile(path=p, text=t, size_bytes=len(t.encode()))


def _run(*names: str):
    return registry.get("iceberg.metadata").analyze(_req(), [_inp(n) for n in names])


class TestParser:
    def test_v1_basic(self):
        m = parse_metadata((FX / "v1_simple.json").read_text(encoding="utf-8"))
        assert m.format_version == 1
        assert len(m.snapshots) == 1
        assert m.snapshots[0].manifest_list.startswith("s3://")
        assert m.partition_specs[0].fields[0].transform == "day"
        assert m.refs["main"]["snapshot-id"] == 1

    def test_v2_evolution(self):
        m = parse_metadata((FX / "v2_evolved.json").read_text(encoding="utf-8"))
        assert m.format_version == 2
        assert len(m.schemas) == 2 and len(m.partition_specs) == 2
        assert m.snapshots[1].sequence_number == 1
        assert m.partition_specs[1].fields[1].transform == "void"

    def test_v3_unknown_fields_preserved(self):
        m = parse_metadata((FX / "v3_unknown_fields.json").read_text(encoding="utf-8"))
        assert m.format_version == 3
        assert "next-row-id" in m.extras and "row-lineage" in m.extras

    def test_malformed_raises_parse_error(self):
        with pytest.raises(MetadataParseError):
            parse_metadata((FX / "malformed.json").read_text(encoding="utf-8"))

    def test_non_object_rejected(self):
        with pytest.raises(MetadataParseError):
            parse_metadata("[1,2,3]")

    def test_oversized_rejected(self):
        with pytest.raises(MetadataParseError, match="excede"):
            parse_metadata('{"format-version":2,"x":"' + "A" * (17 * 1024 * 1024) + '"}')

    def test_deep_nesting_rejected(self):
        deep = '{"format-version":2,"x":' + "[" * 100 + "]" * 100 + "}"
        with pytest.raises(MetadataParseError, match="profundidade"):
            parse_metadata(deep)

    def test_http_location_warns_not_followed(self):
        m = parse_metadata('{"format-version":2,"location":"https://evil/t"}')
        assert any("https" in w for w in m.warnings)

    def test_unknown_format_warns(self):
        m = parse_metadata('{"format-version":9}')
        assert m.format_version == -1
        assert m.warnings


class TestAnalyzer:
    def test_registered(self):
        assert registry.get("iceberg.metadata").analyzer_id == "iceberg.metadata"

    def test_v1_clean_no_findings(self):
        r = _run("v1_simple.json")
        assert r.findings == []
        assert r.metadata["tables"][0]["format_version"] == 1

    def test_inconsistent_current_snapshot(self):
        r = _run("inconsistent_current.json")
        f = next(f for f in r.findings if "current-snapshot-id" in f.explanation)
        assert f.status == FindingStatus.CONFIRMED
        assert f.category == FindingCategory.DATA_QUALITY

    def test_schema_evolution_confirmed(self):
        r = _run("v2_evolved.json")
        f = next(f for f in r.findings if "Evolução de schema" in f.explanation)
        assert f.status == FindingStatus.CONFIRMED
        assert f.evidence_ids  # linked evidence exists

    def test_void_transform_findings(self):
        r = _run("v2_evolved.json")
        assert any("void" in f.explanation for f in r.findings)

    def test_small_files_conditional(self):
        # v2: 2GB/500=4MB e 3GB/800=4MB < 32MB → indício POSSIBLE
        r = _run("v2_evolved.json")
        f = next(f for f in r.findings if "small files" in f.explanation)
        assert f.status == FindingStatus.POSSIBLE  # nunca CONFIRMED sem observação

    def test_no_small_files_when_large(self):
        r = _run("v1_simple.json")  # 256MB/4 = 64MB médio
        assert not any("small files" in f.explanation for f in r.findings)

    def test_retention_hypothesis(self):
        r = _run("many_snapshots.json")
        f = next(f for f in r.findings if "retenção" in f.explanation)
        assert f.status == FindingStatus.POSSIBLE

    def test_orphan_parent_recorded_as_evidence(self):
        r = _run("v2_evolved.json")  # snapshot 3 → parent 99 ausente
        assert any("parent" in e.sanitized_excerpt for e in r.evidence)

    def test_malformed_becomes_limitation_not_crash(self):
        r = _run("malformed.json")
        assert any("JSON inválido" in lim for lim in r.limitations)
        assert r.findings[0].status == FindingStatus.UNKNOWN

    def test_declared_provenance_all_evidence(self):
        r = _run("v2_evolved.json")
        assert all(e.provenance == "declared" for e in r.evidence)

    def test_unknown_fields_reported_as_limitation(self):
        r = _run("v3_unknown_fields.json")
        assert any("next-row-id" in lim for lim in r.limitations)

    def test_capabilities_manifest(self):
        a = registry.get("iceberg.metadata")
        cap = a.capabilities()
        assert "glue-5.1" in cap.supported_runtimes
        assert "analyze_iceberg_metadata" in cap.supported_operations
