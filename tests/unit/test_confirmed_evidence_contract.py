"""Contract test (ds-0104 §7.2): CONFIRMED findings must cite evidence.

Two layers against regression:

1. Static — AST-scan ``src/data_sentinel/**/*.py`` and assert no
   ``Finding(...)`` call that references ``FindingStatus.CONFIRMED`` lacks
   an ``evidence_ids=`` keyword (or passes an empty literal).
2. Runtime — run analyzers over existing fixtures and assert every CONFIRMED
   finding carries non-empty ``evidence_ids``.
"""

import ast
from pathlib import Path

from data_sentinel.analyzers.iceberg.analyzer import IcebergMetadataAnalyzer
from data_sentinel.analyzers.spark import SparkGlueLogAnalyzer
from data_sentinel.analyzers.spark.plans import SparkPlanAnalyzer
from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    FindingStatus,
    Platform,
    SourceType,
)
from data_sentinel.core.security import InputFile

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "data_sentinel"
FIXTURES = ROOT / "fixtures"


def _is_finding_call(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Name)
        and func.id == "Finding"
        or isinstance(func, ast.Attribute)
        and func.attr == "Finding"
    )


def _references_confirmed(call: ast.Call) -> bool:
    return any(
        isinstance(n, ast.Attribute) and n.attr == "CONFIRMED"
        for n in ast.walk(call)
    )


def _has_evidence_kwarg(call: ast.Call) -> bool:
    for kw in call.keywords:
        if kw.arg == "evidence_ids":
            return not (
                isinstance(kw.value, (ast.List, ast.Tuple))
                and not kw.value.elts
            )
    return False


def _inp(path: Path) -> InputFile:
    text = path.read_text(encoding="utf-8")
    return InputFile(path=path, text=text, size_bytes=path.stat().st_size)


class TestStaticContract:
    def test_no_confirmed_finding_without_evidence_ids(self) -> None:
        violations: list[str] = []
        for path in sorted(SRC.rglob("*.py")):
            tree = ast.parse(
                path.read_text(encoding="utf-8"), filename=str(path)
            )
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and _is_finding_call(node)
                    and _references_confirmed(node)
                    and not _has_evidence_kwarg(node)
                ):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}"
                    )
        assert violations == []


class TestRuntimeContract:
    def _run(self, analyzer, source_type: SourceType, platform: Platform,
             paths: list[Path]):
        request = DiagnosticRequest(
            source_type=source_type,
            artifact_references=[
                ArtifactReference(uri=f"file://{p.name}") for p in paths
            ],
            platform=platform,
        )
        return analyzer.analyze(request, [_inp(p) for p in paths])

    def test_confirmed_findings_have_evidence(self) -> None:
        cases = [
            (
                IcebergMetadataAnalyzer(),
                SourceType.ICEBERG_METADATA,
                Platform.AWS_GLUE,
                [
                    FIXTURES / "iceberg" / "inconsistent_current.json",
                    FIXTURES / "iceberg" / "many_snapshots.json",
                ],
            ),
            (
                SparkPlanAnalyzer(),
                SourceType.SPARK_PLAN,
                Platform.SPARK,
                [FIXTURES / "plans" / "cartesian.txt"],
            ),
            (
                SparkGlueLogAnalyzer(),
                SourceType.LOG,
                Platform.AWS_GLUE,
                [FIXTURES / "logs" / "glue_oom.log"],
            ),
        ]
        confirmed = 0
        for analyzer, source_type, platform, paths in cases:
            result = self._run(analyzer, source_type, platform, paths)
            for finding in result.findings:
                if finding.status == FindingStatus.CONFIRMED:
                    confirmed += 1
                    assert finding.evidence_ids, (
                        f"{analyzer.analyzer_id}: CONFIRMED finding sem "
                        f"evidence_ids: {finding.explanation[:80]}"
                    )
        assert confirmed > 0  # fixtures must exercise CONFIRMED paths
