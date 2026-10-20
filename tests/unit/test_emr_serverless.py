"""EMR Serverless tests (ds-0062)."""

from pathlib import Path

from data_sentinel.analyzers.emr import EmrServerlessAnalyzer
from data_sentinel.core.contracts.entities import ArtifactReference, DiagnosticRequest
from data_sentinel.core.contracts.enums import FindingStatus, Platform, SourceType
from data_sentinel.core.security import InputFile

FX = Path(__file__).parent.parent / "fixtures" / "emr-serverless-failed.json"


def _run():
    req = DiagnosticRequest(
        source_type=SourceType.OTHER,
        artifact_references=[ArtifactReference(uri=str(FX))],
        platform=Platform.SPARK)
    inp = InputFile(path=FX, text=FX.read_text(),
                    size_bytes=FX.stat().st_size)
    return EmrServerlessAnalyzer().analyze(req, [inp])


def test_failed_job_oom_confirmed() -> None:
    r = _run()
    fails = [f for f in r.findings if "falhou" in f.explanation]
    assert fails and fails[0].status == FindingStatus.CONFIRMED
    assert fails[0].category.value == "out_of_memory"


def test_retry_and_slow_startup() -> None:
    r = _run()
    assert any("tentativa 2" in f.explanation for f in r.findings)
    slow = [f for f in r.findings if "slow startup" in f.explanation]
    assert slow and slow[0].recommendations


def test_cost_is_estimated_never_billing() -> None:
    r = _run()
    cost = [f for f in r.findings if f.category.value == "cost"]
    assert cost
    assert "ESTIMADO" in cost[0].explanation
    assert "billing" in str(cost[0].alternatives)
