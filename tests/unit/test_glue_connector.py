"""Glue connector tests — botocore Stubber, zero real AWS access."""

from datetime import UTC, datetime
from typing import Any, ClassVar

import pytest
from botocore.stub import Stubber

from data_sentinel.connectors.aws import ALLOWED_ACTIONS, GlueConnector
from data_sentinel.connectors.aws.errors import AwsConnectorError, map_client_error
from data_sentinel.connectors.aws.sessions import build_session, require_boto3
from data_sentinel.core.exceptions import SentinelError


@pytest.fixture
def stubbed() -> Any:
    import boto3

    session = boto3.session.Session(
        aws_access_key_id="test",
        aws_secret_access_key="test",  # noqa: S106 — fake stub creds
        region_name="us-east-1",
    )
    client = session.client("glue")
    stubber = Stubber(client)
    stubber.activate()
    yield session, client, stubber
    stubber.deactivate()


def _connector(session: Any, client: Any) -> GlueConnector:
    conn = GlueConnector(session)
    conn._client = client  # inject stubbed client
    return conn


JOB = {
    "Job": {
        "Name": "job1",
        "GlueVersion": "4.0",
        "Command": {"Name": "glueetl", "ScriptLocation": "s3://b/s.py"},
        "Role": "arn:aws:iam::1:role/glue",
        "WorkerType": "G.1X",
        "NumberOfWorkers": 10,
        "Timeout": 60,
        "DefaultArguments": {
            "--db_password": "supersecret",
            "--table": "orders",
        },
    }
}


class TestGetJob:
    def test_get_job_maps_and_sanitizes(self, stubbed: Any) -> None:
        session, client, stub = stubbed
        stub.add_response("get_job", JOB, {"JobName": "job1"})
        job = _connector(session, client).get_job("job1")
        assert job.name == "job1"
        assert job.glue_version == "4.0"
        assert job.worker_type == "G.1X"
        assert job.default_arguments["--table"] == "orders"
        assert "supersecret" not in str(job.default_arguments)
        assert "«redacted" in job.default_arguments["--db_password"]

    def test_get_job_not_found(self, stubbed: Any) -> None:
        session, client, stub = stubbed
        stub.add_client_error(
            "get_job", "EntityNotFoundException", "not found", http_status_code=404
        )
        with pytest.raises(AwsConnectorError) as err:
            _connector(session, client).get_job("nope")
        assert err.value.code == "aws.nao_encontrado"

    def test_get_job_access_denied(self, stubbed: Any) -> None:
        session, client, stub = stubbed
        stub.add_client_error("get_job", "AccessDeniedException", "denied")
        with pytest.raises(AwsConnectorError) as err:
            _connector(session, client).get_job("job1")
        assert err.value.code == "aws.acesso_negado"


class TestJobRuns:
    RUNS: ClassVar[dict] = {
        "JobRuns": [
            {
                "Id": "jr_2",
                "JobRunState": "FAILED",
                "Attempt": 1,
                "StartedOn": datetime(2026, 1, 2, tzinfo=UTC),
                "ExecutionTime": 300,
                "ErrorMessage": "An error with password=hidden in it",
                "DPUSeconds": 42.0,
                "LogGroupName": "/aws-glue/jobs",
            },
            {
                "Id": "jr_1",
                "JobRunState": "SUCCEEDED",
                "Attempt": 1,
                "StartedOn": datetime(2026, 1, 1, tzinfo=UTC),
                "ExecutionTime": 100,
            },
        ]
    }

    def test_get_job_runs_orders_and_sanitizes(self, stubbed: Any) -> None:
        session, client, stub = stubbed
        stub.add_response(
            "get_job_runs",
            self.RUNS,
            {"JobName": "job1", "MaxResults": 50},
        )
        runs = list(_connector(session, client).get_job_runs("job1"))
        assert [r.run_id for r in runs] == ["jr_2", "jr_1"]  # newest first
        assert runs[0].status == "FAILED"
        assert runs[0].dpu_seconds == 42.0
        assert "password=hidden" not in (runs[0].error_message or "")

    def test_get_job_run_single(self, stubbed: Any) -> None:
        session, client, stub = stubbed
        stub.add_response(
            "get_job_run",
            {"JobRun": self.RUNS["JobRuns"][0]},
            {"JobName": "job1", "RunId": "jr_2", "PredecessorsIncluded": False},
        )
        run = _connector(session, client).get_job_run("job1", "jr_2")
        assert run.run_id == "jr_2" and run.status == "FAILED"

    def test_pagination(self, stubbed: Any) -> None:
        session, client, stub = stubbed
        stub.add_response(
            "get_job_runs",
            {"JobRuns": [self.RUNS["JobRuns"][0]], "NextToken": "t2"},
            {"JobName": "job1", "MaxResults": 2},
        )
        stub.add_response(
            "get_job_runs",
            {"JobRuns": [self.RUNS["JobRuns"][1]]},
            {"JobName": "job1", "MaxResults": 1, "NextToken": "t2"},
        )
        runs = list(_connector(session, client).get_job_runs("job1", limit=2))
        assert [r.run_id for r in runs] == ["jr_2", "jr_1"]

    def test_cancellation(self, stubbed: Any) -> None:
        session, client, stub = stubbed
        calls = iter([False, True])
        stub.add_response(
            "get_job_runs",
            {"JobRuns": self.RUNS["JobRuns"]},
            {"JobName": "job1", "MaxResults": 50},
        )
        runs = list(
            _connector(session, client).get_job_runs(
                "job1", cancelled=lambda: next(calls, True)
            )
        )
        assert len(runs) <= 1


class TestReadOnlyAndSafety:
    def test_allowlist_only_readonly(self) -> None:
        assert {
            "get_job",
            "get_jobs",
            "get_job_run",
            "get_job_runs",
        } == ALLOWED_ACTIONS
        mutating = {"start_job_run", "stop_job_run", "update_job", "delete_job", "create_job"}
        assert ALLOWED_ACTIONS.isdisjoint(mutating)

    def test_non_allowlisted_call_rejected(self, stubbed: Any) -> None:
        session, client, _ = stubbed
        conn = _connector(session, client)
        with pytest.raises(SentinelError) as err:
            conn._call("start_job_run", JobName="j")
        assert err.value.code == "aws.acao_nao_permitida"

    def test_offline_profile_blocks(self, stubbed: Any) -> None:
        session, _, _ = stubbed
        with pytest.raises(SentinelError) as err:
            GlueConnector(session, allow_network=False)
        assert err.value.code == "aws.offline"

    def test_no_boto3_hint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "boto3":
                raise ImportError("no boto3")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(SentinelError) as err:
            require_boto3()
        assert err.value.code == "aws.boto3_ausente"
        with pytest.raises(SentinelError):
            build_session()


class TestErrorTaxonomy:
    def test_throttling_maps(self) -> None:
        err = map_client_error(
            _FakeClientError("ThrottlingException", "rate exceeded"),
            context="ctx",
        )
        assert err.code == "aws.throttling"

    def test_expired_token_maps(self) -> None:
        err = map_client_error(
            _FakeClientError("ExpiredTokenException", "expired"), context="ctx"
        )
        assert err.code == "aws.token_expirado"

    def test_no_credentials_maps(self) -> None:
        from botocore.exceptions import NoCredentialsError

        err = map_client_error(NoCredentialsError(), context="ctx")
        assert err.code == "aws.sem_credenciais"

    def test_profile_not_found_maps(self) -> None:
        from botocore.exceptions import ProfileNotFound

        err = map_client_error(ProfileNotFound(profile="x"), context="ctx")
        assert err.code == "aws.perfil_inexistente"


class _FakeClientError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.response = {"Error": {"Code": code, "Message": message}}
