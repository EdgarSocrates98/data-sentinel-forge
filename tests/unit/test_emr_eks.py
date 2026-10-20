"""EMR on EKS tests (ds-0063)."""

from pathlib import Path

from data_sentinel.analyzers.emr import EmrEksAnalyzer
from data_sentinel.core.contracts.entities import ArtifactReference, DiagnosticRequest
from data_sentinel.core.contracts.enums import FindingStatus, Platform, SourceType
from data_sentinel.core.security import InputFile

FX = Path(__file__).parent.parent / "fixtures" / "emr-eks-pods.yaml"


def _run():
    req = DiagnosticRequest(
        source_type=SourceType.OTHER,
        artifact_references=[ArtifactReference(uri=str(FX))],
        platform=Platform.SPARK)
    inp = InputFile(path=FX, text=FX.read_text(),
                    size_bytes=FX.stat().st_size)
    return EmrEksAnalyzer().analyze(req, [inp])


def test_oomkilled_driver_confirmed() -> None:
    r = _run()
    oom = [f for f in r.findings
           if f.category.value == "out_of_memory"]
    assert oom and oom[0].status == FindingStatus.CONFIRMED
    assert "driver" in oom[0].explanation.lower()


def test_unschedulable_executor() -> None:
    r = _run()
    us = [f for f in r.findings
          if "unschedulable" in f.explanation]
    assert us and us[0].status == FindingStatus.CONFIRMED


def test_scheduling_event_detected() -> None:
    r = _run()
    assert any("Scheduling failure" in f.explanation
               for f in r.findings)
