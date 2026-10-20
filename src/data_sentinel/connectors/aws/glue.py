"""Read-only AWS Glue connector.

Enforces an explicit allowlist of read-only API actions — no mutating Glue
call is reachable through this object (ADR 0009). Returns internal models,
never raw boto3 dicts (see connectors/aws/models.py).
"""

import re
import time
from collections.abc import Callable, Iterator
from typing import Any

from data_sentinel.connectors.aws.errors import map_client_error
from data_sentinel.connectors.aws.models import GlueJob, GlueJobRun
from data_sentinel.core.exceptions import SentinelError
from data_sentinel.core.security import sanitize_evidence_excerpt

ALLOWED_ACTIONS: frozenset[str] = frozenset(
    {
        "get_job",
        "get_jobs",
        "get_job_run",
        "get_job_runs",
    }
)

_SECRET_KEY = re.compile(r"(?i)(pass(word)?|secret|token|key|credential|pwd)")

_RETRYABLE = frozenset({"ThrottlingException", "TooManyRequestsException"})


def _sanitize_args(arguments: dict[str, Any] | None) -> dict[str, str]:
    """Sanitize Glue arguments — mask secret-looking keys, redact values."""
    out: dict[str, str] = {}
    for key, value in (arguments or {}).items():
        k = str(key)
        if _SECRET_KEY.search(k):
            out[k] = "«redacted:arg»"
        else:
            out[k] = sanitize_evidence_excerpt(str(value))
    return out


class GlueConnector:
    """Read-only Glue metadata access.

    allow_network=False refuses instantiation — the offline profile cannot
    reach AWS by construction.
    """

    def __init__(
        self,
        session: Any,
        *,
        allow_network: bool = True,
        max_retries: int = 4,
        backoff_base: float = 0.5,
    ) -> None:
        if not allow_network:
            raise SentinelError(
                code="aws.offline",
                message=(
                    "perfil offline bloqueia acesso à AWS — "
                    "mude de perfil ou analise artefatos locais"
                ),
                details={},
            )
        self._session = session
        self._max_retries = max_retries
        self._backoff = backoff_base
        try:
            self._client = session.client("glue")
        except Exception as exc:
            raise map_client_error(exc, context="criar cliente Glue") from exc

    # -- read-only enforcement ------------------------------------------------

    def _call(self, api: str, **params: Any) -> Any:
        """Single funnel for every AWS call — allowlist + retry + taxonomy."""
        if api not in ALLOWED_ACTIONS:
            raise SentinelError(
                code="aws.acao_nao_permitida",
                message=f"ação '{api}' não está na allowlist read-only do conector",
                details={"api": api, "allowed": sorted(ALLOWED_ACTIONS)},
            )
        attempt = 0
        while True:
            try:
                return getattr(self._client, api)(**params)
            except Exception as exc:
                code = str(getattr(exc, "response", {}).get("Error", {}).get("Code", ""))
                if code in _RETRYABLE and attempt < self._max_retries:
                    time.sleep(self._backoff * (2**attempt))
                    attempt += 1
                    continue
                raise map_client_error(exc, context=f"glue:{api}") from exc

    # -- operations ------------------------------------------------------------

    def get_job(self, name: str) -> GlueJob:
        """Fetch a single job definition (sanitized)."""
        resp = self._call("get_job", JobName=name)
        return self._to_job(resp.get("Job", {}), name)

    def get_jobs(self, *, limit: int = 50) -> list[GlueJob]:
        """List jobs with bounded pagination."""
        jobs: list[GlueJob] = []
        token: str | None = None
        while len(jobs) < limit:
            params: dict[str, Any] = {"MaxResults": min(50, limit - len(jobs))}
            if token:
                params["NextToken"] = token
            resp = self._call("get_jobs", **params)
            jobs.extend(self._to_job(j, j.get("Name", "?")) for j in resp.get("Jobs", []))
            token = resp.get("NextToken")
            if not token:
                break
        return jobs

    def get_job_run(self, job_name: str, run_id: str, *, predecessors: bool = False) -> GlueJobRun:
        """Fetch one run (sanitized)."""
        resp = self._call(
            "get_job_run",
            JobName=job_name,
            RunId=run_id,
            PredecessorsIncluded=predecessors,
        )
        run = resp.get("JobRun", {})
        pred = None
        if predecessors and run.get("PredecessorRuns"):
            pred = run["PredecessorRuns"][0].get("Id")
        return self._to_run(job_name, run, predecessor=pred)

    def get_job_runs(
        self,
        job_name: str,
        *,
        limit: int = 50,
        cancelled: Callable[[], bool] | None = None,
    ) -> Iterator[GlueJobRun]:
        """Yield runs newest-first with bounded pagination + cancellation."""
        yielded = 0
        token: str | None = None
        while yielded < limit:
            if cancelled is not None and cancelled():
                return
            params: dict[str, Any] = {
                "JobName": job_name,
                "MaxResults": min(50, limit - yielded),
            }
            if token:
                params["NextToken"] = token
            resp = self._call("get_job_runs", **params)
            runs = resp.get("JobRuns", [])
            if not runs:
                return
            for run in sorted(runs, key=lambda r: r.get("StartedOn") or 0, reverse=True):
                if cancelled is not None and cancelled():
                    return
                yield self._to_run(job_name, run)
                yielded += 1
                if yielded >= limit:
                    return
            token = resp.get("NextToken")
            if not token:
                return

    # -- mapping ----------------------------------------------------------------

    @staticmethod
    def _to_job(j: dict[str, Any], name: str) -> GlueJob:
        command = j.get("Command", {}) or {}
        conns = j.get("Connections", {}) or {}
        return GlueJob(
            name=j.get("Name", name),
            description=j.get("Description"),
            glue_version=j.get("GlueVersion"),
            command_name=command.get("Name"),
            command_script_location=command.get("ScriptLocation"),
            role=j.get("Role"),
            worker_type=j.get("WorkerType"),
            number_of_workers=j.get("NumberOfWorkers"),
            max_capacity=j.get("MaxCapacity"),
            timeout_minutes=j.get("Timeout"),
            execution_class=j.get("ExecutionClass"),
            security_configuration=j.get("SecurityConfiguration"),
            default_arguments=_sanitize_args(j.get("DefaultArguments")),
            connections=list(conns.get("Connections", [])),
            raw_keys_present=sorted(j.keys()),
        )

    @staticmethod
    def _to_run(job_name: str, r: dict[str, Any], *, predecessor: str | None = None) -> GlueJobRun:
        return GlueJobRun(
            job_name=job_name,
            run_id=r.get("Id", ""),
            status=r.get("JobRunState", "UNKNOWN"),
            attempt=r.get("Attempt"),
            started_on=r.get("StartedOn"),
            completed_on=r.get("CompletedOn"),
            execution_time_seconds=r.get("ExecutionTime"),
            error_message=(
                sanitize_evidence_excerpt(r["ErrorMessage"]) if r.get("ErrorMessage") else None
            ),
            glue_version=r.get("GlueVersion"),
            worker_type=r.get("WorkerType"),
            number_of_workers=r.get("NumberOfWorkers"),
            dpu_seconds=r.get("DPUSeconds"),
            log_group_name=r.get("LogGroupName"),
            arguments=_sanitize_args(r.get("Arguments")),
            predecessor_run_id=predecessor,
        )
