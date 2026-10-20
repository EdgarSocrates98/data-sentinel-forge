"""ds-0024 — cross-account diagnostics + permissions graph."""

from pathlib import Path

from data_sentinel.analyzers.protocol import InputFile
from data_sentinel.analyzers.registry import registry
from data_sentinel.core.contracts.entities import (
    ArtifactReference,
    DiagnosticRequest,
)
from data_sentinel.core.contracts.enums import (
    FindingStatus,
    Platform,
    SourceType,
)

FX = Path("fixtures/access")


def _run(name: str):
    p = FX / name
    t = p.read_text()
    req = DiagnosticRequest(
        source_type=SourceType.ACCESS_CONTEXT,
        artifact_references=[ArtifactReference(uri="file://ctx")],
        platform=Platform.AWS_GLUE,
    )
    return registry.get("lakehouse.cross_account").analyze(
        req, [InputFile(path=p, text=t, size_bytes=len(t.encode()))]
    )


class TestGraph:
    def test_graph_nodes_and_edges(self):
        r = _run("cross_read.json")
        g = r.metadata["graphs"][0]["graph"]
        kinds = {n["kind"] for n in g["nodes"]}
        assert {"account", "principal", "catalog", "table", "resource_link"} <= kinds
        types = {e["type"] for e in g["edges"]}
        assert {"ASSUMES_ROLE", "REFERENCES", "SHARES_WITH"} <= types
        provs = {e["provenance"] for e in g["edges"]}
        assert "unverified" in provs  # share nunca confirmado sem grant visível

    def test_unverified_share_not_denial(self):
        r = _run("cross_read.json")
        assert any("unverified" in lim for lim in r.limitations)
        assert any("visibilidade incompleta" in lim for lim in r.limitations)


class TestFindings:
    def test_cross_read_unknown_not_denied(self):
        r = _run("cross_read.json")
        f = next(f for f in r.findings if "cross-account" in f.explanation)
        assert f.status == FindingStatus.UNKNOWN  # nunca DENIED fabricado

    def test_cross_write_possible_with_chain(self):
        r = _run("cross_write.json")
        f = next(f for f in r.findings if "Escrita cross-account" in f.explanation)
        assert f.status == FindingStatus.POSSIBLE
        assert "KMS" in f.explanation and "cadeia" in f.explanation

    def test_unknown_permissions_findings(self):
        r = _run("cross_read.json")
        assert any("parcialmente invisíveis" in f.explanation
                   for f in r.findings)

    def test_same_account_noted(self):
        r = _run("same_account.json")
        assert any("single-account" in lim for lim in r.limitations)

    def test_invalid_context_limitation(self):
        r = _run("invalid.json")
        assert any("não é JSON" in lim for lim in r.limitations)
        assert r.findings[0].status == FindingStatus.UNKNOWN


class TestProtocol:
    def test_registered(self):
        assert registry.get("lakehouse.cross_account").analyzer_id == \
            "lakehouse.cross_account"

    def test_capabilities(self):
        cap = registry.get("lakehouse.cross_account").capabilities()
        assert "analyze_cross_account" in cap.supported_operations
