"""ds-0028 — E2E A-F (§11): cenários completos Cycle 03.

A: Glue 5.1 FGAC + Iceberg + MERGE
B: cross-account read
C: cross-account write (cadeia completa)
D: MERGE com duplicidade controlada
E: metadata rica (snapshots + evolução + small files)
F: evidência insuficiente — sem causa-raiz fabricada
"""

from pathlib import Path

import pytest

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
    SupportStatus,
)
from data_sentinel.core.contracts.lakehouse import AccessContext
from data_sentinel.diagnostics.orchestrator import run_diagnostics
from data_sentinel.knowledge.compat import assess_compatibility
from data_sentinel.lakehouse import resolve

ROOT = Path(__file__).resolve().parents[2]


def _req(st: SourceType) -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=st,
        artifact_references=[ArtifactReference(uri="e2e://lakehouse")],
        platform=Platform.AWS_GLUE,
    )


def _inp(rel: str) -> InputFile:
    p = ROOT / rel
    return InputFile(path=p, text=p.read_text(encoding="utf-8"), size_bytes=p.stat().st_size)


def _run(st: SourceType, rel: str):
    return run_diagnostics(_req(st), [_inp(rel)])


def _analyze(analyzer_id: str, st: SourceType, rel: str):
    return registry.get(analyzer_id).analyze(_req(st), [_inp(rel)])


class TestE2E_A_Glue51FgacMerge:
    """A: Glue 5.1 + FGAC + Iceberg + MERGE — avaliação completa."""

    def test_assessment_and_operation(self):
        a = assess_compatibility(
            None, runtime="glue-5.1", operation="merge",
            access_mode="fgac", table_format="iceberg")
        assert a.support_status == SupportStatus.SUPPORTED_WITH_CONSTRAINTS
        assert a.documentation_references  # fonte registrada

        out = _run(SourceType.SQL_QUERY, "fixtures/operations/merge_dups.json")
        texts = "\n".join(f.explanation for f in out.report.findings)
        assert "1400 chaves duplicadas" in texts

        ctx = resolve(
            [],
            assessments=[a],
            access=AccessContext(lf_mode="fgac", required_operation="merge"),
        )
        assert ctx.worst_status == SupportStatus.SUPPORTED_WITH_CONSTRAINTS


class TestE2E_B_CrossAccountRead:
    def test_unknown_not_denied(self):
        out = _run(SourceType.ACCESS_CONTEXT, "fixtures/access/cross_read.json")
        texts = "\n".join(f.explanation for f in out.report.findings)
        assert "cross-account" in texts
        assert not any(f.status == FindingStatus.CONFIRMED and "denied" in
                       f.explanation.lower() for f in out.report.findings)


class TestE2E_C_CrossAccountWrite:
    def test_full_chain_possible(self):
        acc = _analyze("lakehouse.cross_account", SourceType.ACCESS_CONTEXT,
                       "fixtures/access/cross_write.json")
        pol = _analyze("iam.policy", SourceType.POLICY_DOC,
                       "fixtures/policies/cross_kms.json")
        ops = _analyze("lakehouse.operation", SourceType.SQL_QUERY,
                       "fixtures/operations/merge_dups.json")
        ctx = resolve([acc, pol, ops])
        texts = "\n".join(f.explanation for f in ctx.findings)
        # cada elo da cadeia aparece
        assert "Escrita cross-account" in texts
        assert "KMS" in texts or "chaves" in texts
        assert "duplicadas" in texts
        # nada confirmado como autorizado
        assert not any("autorizado" in f.explanation.lower()
                       for f in ctx.findings)


class TestE2E_D_MergeDuplicates:
    def test_declared_dups_confirmed(self):
        out = _run(SourceType.SQL_QUERY, "fixtures/operations/merge_dups.json")
        f = next(f for f in out.report.findings
                 if "duplicadas" in f.explanation)
        assert f.status == FindingStatus.CONFIRMED
        assert f.evidence_ids  # evidência citada
        assert any("FONTE" in r or "fonte" in r for r in f.recommendations)


class TestE2E_E_RichMetadata:
    def test_evolution_and_maintenance(self):
        out = _run(SourceType.ICEBERG_METADATA,
                   "fixtures/iceberg/v2_evolved.json")
        texts = "\n".join(f.explanation for f in out.report.findings)
        assert "Evolução de schema" in texts
        assert "void" in texts
        assert "small files" in texts
        assert all(e.provenance == "declared" for e in out.evidence)


class TestE2E_F_InsufficientEvidence:
    def test_no_fabricated_root_cause(self):
        out = _run(SourceType.ICEBERG_METADATA,
                   "fixtures/iceberg/malformed.json")
        assert out.report.findings
        assert out.report.findings[0].status == FindingStatus.UNKNOWN
        assert any("JSON" in lim for lim in out.report.limitations)
        # nenhuma causa-raiz afirmada
        assert not any(f.status == FindingStatus.CONFIRMED
                       for f in out.report.findings)


@pytest.mark.skipif(
    not __import__("os").environ.get("DATA_SENTINEL_AWS_TESTS"),
    reason="env-gated: real AWS non-prod credentials required",
)
class TestAwsRealHomologation:
    """§10.2 — tentativa de homologação real. BLOCKED sem credenciais."""

    def test_glue_get_job_readonly(self):
        import boto3

        client = boto3.client("glue", region_name="us-east-1")
        # leitura real autorizada apenas — nenhum call mutante
        client.list_jobs(MaxResults=1)
