"""CloudWatch diagnostics tests — parser, correlation, timeline, connectors."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from botocore.stub import Stubber

from data_sentinel.analyzers.cloudwatch import CloudWatchLogAnalyzer, parse_log_text
from data_sentinel.connectors.aws.cloudwatch_logs import (
    ALLOWED_ACTIONS as LOGS_ACTIONS,
)
from data_sentinel.connectors.aws.cloudwatch_logs import (
    CloudWatchLogsConnector,
)
from data_sentinel.connectors.aws.cloudwatch_metrics import (
    ALLOWED_ACTIONS as METRICS_ACTIONS,
)
from data_sentinel.connectors.aws.cloudwatch_metrics import (
    CloudWatchMetricsConnector,
)
from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    FindingStatus,
    Platform,
    SourceType,
)
from data_sentinel.core.security.paths import InputFile
from data_sentinel.diagnostics.correlation import correlate
from data_sentinel.diagnostics.timeline import build_timeline

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "cloudwatch"


def _input(path: Path) -> InputFile:
    return InputFile(path=path, text=path.read_text(), size_bytes=path.stat().st_size)


def _request() -> DiagnosticRequest:
    return DiagnosticRequest(
        source_type=SourceType.CLOUDWATCH_LOG,
        artifact_references=[ArtifactReference(uri="mem://cw")],
        platform=Platform.AWS_GLUE,
    )


class TestLogParser:
    def test_parses_exceptions_and_timestamps(self) -> None:
        parsed = parse_log_text((FIXTURES / "glue_failure_events.log").read_text())
        assert len(parsed.exceptions) == 3
        assert parsed.exceptions[0].exception_class == "OutOfMemoryError"
        assert all(e.timestamp for e in parsed.events)

    def test_chained_exception_marked(self) -> None:
        parsed = parse_log_text((FIXTURES / "chained_exceptions.log").read_text())
        chained = [e for e in parsed.events if e.is_chained]
        assert len(chained) >= 1
        assert any(e.exception_class == "OutOfMemoryError" for e in chained)

    def test_unknown_lines_pass_through(self) -> None:
        parsed = parse_log_text((FIXTURES / "no_exceptions.log").read_text())
        assert parsed.exceptions == []
        assert parsed.unparsed_lines >= 1

    def test_known_exception_coverage(self) -> None:
        text = (
            "e Py4JJavaError: x\n"
            "e FetchFailedException: y\n"
            "e AnalysisException: z\n"
            "e PermissionDeniedException: w\n"
        )
        parsed = parse_log_text(text)
        classes = {e.exception_class for e in parsed.exceptions}
        assert {"Py4JJavaError", "FetchFailedException", "AnalysisException"} <= classes


class TestCorrelation:
    def test_primary_vs_cascade(self) -> None:
        parsed = parse_log_text((FIXTURES / "glue_failure_events.log").read_text())
        result = correlate(parsed)
        assert result.incidents[0].primary is not None
        assert result.incidents[0].primary.exception_class == "OutOfMemoryError"
        cascades = {e.exception_class for e in result.incidents[0].secondary}
        assert "FetchFailedException" in cascades

    def test_chained_attached_to_primary(self) -> None:
        parsed = parse_log_text((FIXTURES / "chained_exceptions.log").read_text())
        result = correlate(parsed)
        assert result.chained_count >= 1
        assert result.incidents[0].secondary  # chained attached, not primary

    def test_no_exceptions_single_inconclusive_incident(self) -> None:
        parsed = parse_log_text((FIXTURES / "no_exceptions.log").read_text())
        result = correlate(parsed)
        assert result.incidents and result.incidents[0].primary is None

    def test_independent_exceptions_open_new_incident(self) -> None:
        text = (
            "2026-01-01T10:00:00 ERROR java.lang.OutOfMemoryError: heap\n"
            "2026-01-02T10:00:00 ERROR com.x.AccessDeniedException: denied\n"
        )
        result = correlate(parse_log_text(text), window_seconds=60)
        assert len(result.incidents) == 2


class TestTimeline:
    def test_entries_carry_real_timestamps(self) -> None:
        parsed = parse_log_text((FIXTURES / "glue_failure_events.log").read_text())
        tl = build_timeline(parsed)
        assert len(tl.entries) >= 5
        assert all(e.timestamp for e in tl.entries)
        assert tl.entries[0].timestamp <= tl.entries[-1].timestamp

    def test_render_format(self) -> None:
        parsed = parse_log_text((FIXTURES / "glue_failure_events.log").read_text())
        out = build_timeline(parsed).render()
        assert "14:09:10" in out and "OutOfMemoryError" in out

    def test_undated_lines_counted(self) -> None:
        parsed = parse_log_text((FIXTURES / "no_exceptions.log").read_text())
        tl = build_timeline(parsed)
        assert tl.undated_lines >= 1


class TestAnalyzer:
    def test_cascade_finding_demoted(self) -> None:
        analyzer = CloudWatchLogAnalyzer()
        result = analyzer.analyze(_request(), [_input(FIXTURES / "glue_failure_events.log")])
        assert result.duration_ms is not None
        corr = result.metadata["correlation"]
        assert corr["incident_count"] >= 1
        assert result.metadata["timeline"]
        # spark-exception signature appears only as cascade → not CONFIRMED
        for f in result.findings:
            if "cascata" in f.explanation:
                assert f.status == FindingStatus.PROBABLE

    def test_capabilities_valid(self) -> None:
        m = CloudWatchLogAnalyzer().capabilities()
        assert m.capability_id == "cloudwatch-log-analyzer"
        assert "correlate_errors" in m.supported_operations

    def test_source_type_registered(self) -> None:
        from data_sentinel.analyzers import registry

        assert registry.for_source_type(SourceType.CLOUDWATCH_LOG)


class TestLogsConnector:
    def _conn(self, client: Any) -> CloudWatchLogsConnector:
        import boto3

        session = boto3.session.Session(
            aws_access_key_id="t", aws_secret_access_key="t", region_name="us-east-1"  # noqa: S106
        )
        conn = CloudWatchLogsConnector(session)
        conn._client = client
        return conn

    def _stubbed(self) -> Any:
        import boto3

        session = boto3.session.Session(
            aws_access_key_id="t", aws_secret_access_key="t", region_name="us-east-1"  # noqa: S106
        )
        client = session.client("logs")
        stub = Stubber(client)
        stub.activate()
        return client, stub

    def test_get_log_events_pages(self) -> None:
        client, stub = self._stubbed()
        stub.add_response(
            "get_log_events",
            {
                "events": [{"timestamp": 1_700_000_000_000, "message": "m1"}],
                "nextForwardToken": "t1",
            },
            {
                "logGroupName": "g",
                "logStreamName": "s",
                "limit": 10_000,
            },
        )
        stub.add_response(
            "get_log_events",
            {"events": [{"timestamp": 1_700_000_001_000, "message": "m2"}]},
            {
                "logGroupName": "g",
                "logStreamName": "s",
                "limit": 10_000,
                "nextToken": "t1",
            },
        )
        events = list(self._conn(client).get_log_events(group="g", stream="s"))
        assert [e.message for e in events] == ["m1", "m2"]
        assert all(e.timestamp for e in events)

    def test_filter_correlates_run_id(self) -> None:
        client, stub = self._stubbed()
        stub.add_response(
            "filter_log_events",
            {
                "events": [
                    {
                        "timestamp": 1_700_000_000_000,
                        "message": "err",
                        "logStreamName": "s1",
                    }
                ]
            },
            {"logGroupName": "g", "limit": 10_000, "filterPattern": "jr_1"},
        )
        events = list(
            self._conn(client).filter_log_events(group="g", filter_pattern="jr_1")
        )
        assert events[0].stream == "s1"

    def test_volume_cap(self) -> None:
        client, stub = self._stubbed()
        stub.add_response(
            "get_log_events",
            {
                "events": [
                    {"timestamp": 1_700_000_000_000 + i, "message": f"m{i}"} for i in range(5)
                ]
            },
            {"logGroupName": "g", "logStreamName": "s", "limit": 2},
        )
        events = list(self._conn(client).get_log_events(group="g", stream="s", limit=2))
        assert len(events) == 2

    def test_allowlist_readonly(self) -> None:
        assert LOGS_ACTIONS.isdisjoint(
            {"put_log_events", "delete_log_group", "create_log_stream"}
        )

    def test_offline_blocked(self) -> None:
        import boto3

        session = boto3.session.Session(
            aws_access_key_id="t", aws_secret_access_key="t", region_name="us-east-1"  # noqa: S106
        )
        from data_sentinel.core.exceptions import SentinelError

        with pytest.raises(SentinelError):
            CloudWatchLogsConnector(session, allow_network=False)


class TestMetricsConnector:
    def _conn(self, client: Any) -> CloudWatchMetricsConnector:
        import boto3

        session = boto3.session.Session(
            aws_access_key_id="t", aws_secret_access_key="t", region_name="us-east-1"  # noqa: S106
        )
        conn = CloudWatchMetricsConnector(session)
        conn._client = client
        return conn

    def test_metric_observations_normalized(self) -> None:
        import boto3

        session = boto3.session.Session(
            aws_access_key_id="t", aws_secret_access_key="t", region_name="us-east-1"  # noqa: S106
        )
        client = session.client("cloudwatch")
        stub = Stubber(client)
        stub.activate()
        stub.add_response(
            "get_metric_statistics",
            {
                "Datapoints": [
                    {
                        "Timestamp": datetime(2026, 1, 1, tzinfo=UTC),
                        "Average": 87.5,
                        "Unit": "Percent",
                    }
                ]
            },
        )
        obs = self._conn(client).get_metric_statistics(
            namespace="Glue",
            metric_name="glue.driver.aggregate.cpu",
            dimensions={"JobName": "j"},
            start=datetime(2026, 1, 1, tzinfo=UTC),
            end=datetime(2026, 1, 1, 1, tzinfo=UTC),
            statistics=("Average",),
        )
        stub.deactivate()
        assert len(obs) == 1
        assert obs[0].quality == "observed"
        assert obs[0].semantics == "gauge"
        assert obs[0].statistic == "Average"

    def test_missing_metric_returns_empty(self) -> None:
        import boto3

        session = boto3.session.Session(
            aws_access_key_id="t", aws_secret_access_key="t", region_name="us-east-1"  # noqa: S106
        )
        client = session.client("cloudwatch")
        stub = Stubber(client)
        stub.activate()
        stub.add_response("get_metric_statistics", {"Datapoints": []})
        obs = self._conn(client).get_metric_statistics(
            namespace="Glue",
            metric_name="m",
            dimensions={},
            start=datetime(2026, 1, 1, tzinfo=UTC),
            end=datetime(2026, 1, 1, 1, tzinfo=UTC),
        )
        stub.deactivate()
        assert obs == []

    def test_allowlist_readonly(self) -> None:
        assert METRICS_ACTIONS.isdisjoint({"put_metric_data", "delete_alarms"})
