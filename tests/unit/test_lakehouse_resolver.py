"""ds-0027 — lakehouse context resolver."""

from pathlib import Path

from data_sentinel.analyzers.protocol import InputFile
from data_sentinel.analyzers.registry import registry
from data_sentinel.core.contracts.entities import (
    ArtifactReference,
    DiagnosticRequest,
)
from data_sentinel.core.contracts.enums import (
    Platform,
    SourceType,
    SupportStatus,
)
from data_sentinel.core.contracts.lakehouse import AccessContext
from data_sentinel.knowledge.compat import assess_compatibility
from data_sentinel.lakehouse import resolve


def _req(st: SourceType) -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=st,
        artifact_references=[ArtifactReference(uri="file://x")],
        platform=Platform.AWS_GLUE,
    )


def _inp(p: Path) -> InputFile:
    t = p.read_text(encoding="utf-8")
    return InputFile(path=p, text=t, size_bytes=len(t.encode()))


def _res(analyzer: str, st: SourceType, path: str):
    return registry.get(analyzer).analyze(_req(st), [_inp(Path(path))])


def test_resolver_merges_domains():
    ice = _res("iceberg.metadata", SourceType.ICEBERG_METADATA,
               "fixtures/iceberg/v2_evolved.json")
    acc = _res("lakehouse.cross_account", SourceType.ACCESS_CONTEXT,
               "fixtures/access/cross_write.json")
    ops = _res("lakehouse.operation", SourceType.SQL_QUERY,
               "fixtures/operations/merge_dups.json")
    assessment = assess_compatibility(
        None, runtime="glue-5.1", operation="merge",
        access_mode="fgac", table_format="iceberg")
    ctx = resolve([ice, acc, ops], assessments=[assessment],
                  access=AccessContext(source_account="1", destination_account="2"))
    assert ctx.iceberg_tables and ctx.graphs and ctx.operations
    assert ctx.assessments[0].support_status == SupportStatus.SUPPORTED_WITH_CONSTRAINTS
    assert ctx.worst_status == SupportStatus.SUPPORTED_WITH_CONSTRAINTS
    assert ctx.access is not None and ctx.access.destination_account == "2"
    d = ctx.to_dict()
    assert d["worst_status"] == "SUPPORTED_WITH_CONSTRAINTS"
    assert d["findings"] >= 3


def test_resolver_empty_is_not_verified():
    ctx = resolve([])
    assert ctx.worst_status == SupportStatus.NOT_VERIFIED
    assert ctx.to_dict()["access"] is None


def test_resolver_propagates_limitations():
    bad = _res("iceberg.metadata", SourceType.ICEBERG_METADATA,
               "fixtures/iceberg/malformed.json")
    ctx = resolve([bad])
    assert any("JSON" in lim for lim in ctx.limitations)
