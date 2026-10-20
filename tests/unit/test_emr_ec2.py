"""EMR EC2 analyzer tests (ds-0061)."""

from pathlib import Path

from data_sentinel.analyzers.emr import EmrEc2Analyzer, parse_cluster
from data_sentinel.core.contracts.entities import ArtifactReference, DiagnosticRequest
from data_sentinel.core.contracts.enums import FindingStatus, Platform, SourceType

FX = Path(__file__).parent.parent / "fixtures" / "emr-ec2-failed-step.json"


def _req() -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=SourceType.OTHER,
        artifact_references=[ArtifactReference(uri=str(FX))],
        platform=Platform.SPARK)


def _analyze():
    from data_sentinel.core.security import InputFile
    inp = InputFile(path=FX, text=FX.read_text(encoding="utf-8"),
                    size_bytes=FX.stat().st_size)
    return EmrEc2Analyzer().analyze(_req(), [inp])


def test_parser_bundle() -> None:
    d = parse_cluster(FX.read_text(encoding="utf-8"))
    assert d.cluster["Id"] == "j-2AXXXXXX"
    assert len(d.steps) == 1 and len(d.instance_groups) == 1


def test_failed_step_oom_categorized() -> None:
    r = _analyze()
    oom = [f for f in r.findings
           if f.category.value == "out_of_memory"]
    assert oom and oom[0].status == FindingStatus.CONFIRMED
    assert oom[0].evidence_ids


def test_bootstrap_failure_confirmed() -> None:
    r = _analyze()
    boot = [f for f in r.findings
            if "terminou com erro" in f.explanation]
    assert boot and boot[0].status == FindingStatus.CONFIRMED


def test_spot_possible_never_confirmed() -> None:
    r = _analyze()
    spot = [f for f in r.findings if "Spot" in f.explanation]
    assert spot and spot[0].status == FindingStatus.POSSIBLE
    assert spot[0].alternatives


def test_empty_doc_honest_unknown() -> None:
    from data_sentinel.core.security import InputFile
    inp = InputFile(path=Path("x.json"), text="{}",
                    size_bytes=2)
    r = EmrEc2Analyzer().analyze(_req(), [inp])
    assert r.findings[0].status == FindingStatus.UNKNOWN
    assert r.findings[0].alternatives
