"""Golden fixture harness (§10.2) — 20 manifests asserting expected,
prohibited findings, evidence and limitations per scenario."""

import json
from pathlib import Path

import pytest

from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    Platform,
    SourceType,
)
from data_sentinel.core.security import InputFile
from data_sentinel.diagnostics.orchestrator import run_diagnostics

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = sorted((ROOT / "fixtures" / "golden").glob("*.json"))


def _run(manifest: dict):
    inp = manifest["input"]
    files = []
    for rel in inp["files"]:
        p = ROOT / rel
        files.append(InputFile(path=p, text=p.read_text(), size_bytes=p.stat().st_size))
    req = DiagnosticRequest(
        source_type=SourceType(inp["source_type"]),
        artifact_references=[ArtifactReference(uri=f"golden://{manifest['id']}")],
        platform=Platform(inp["platform"]),
    )
    return run_diagnostics(req, files)


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=lambda p: p.stem)
def test_golden(manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text())
    out = _run(manifest)
    exp = manifest["expect"]

    texts = [f.explanation for f in out.report.findings]
    all_text = "\n".join(texts)
    for wanted in exp["findings_include"]:
        assert wanted in all_text, (
            f"{manifest['id']}: finding esperado ausente: {wanted!r}\n{all_text}"
        )
    for banned in exp["findings_prohibited"]:
        assert banned not in all_text, (
            f"{manifest['id']}: finding PROIBIDO presente: {banned!r}"
        )
        # prohibited text must also never appear in evidence excerpts
        for ev in out.evidence:
            assert banned not in ev.sanitized_excerpt, (
                f"{manifest['id']}: conteúdo proibido vazou na evidência: {banned!r}"
            )
    if exp["evidence_required"]:
        assert out.evidence, f"{manifest['id']}: evidências esperadas"
    for wanted in exp["limitations_include"]:
        assert any(wanted in lim for lim in out.report.limitations), (
            f"{manifest['id']}: limitação esperada ausente: {wanted!r}"
        )
    if exp.get("redaction_required"):
        assert any("«redacted" in ev.sanitized_excerpt for ev in out.evidence), (
            f"{manifest['id']}: redação esperada nas evidências"
        )
