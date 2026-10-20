"""Read-only CloudWatch Metrics connector (§4.4).

Absent/disabled metrics return empty results — no fabricated series.
"""

from datetime import datetime
from typing import Any

from data_sentinel.connectors.aws.errors import map_client_error
from data_sentinel.connectors.aws.models import MetricObservation
from data_sentinel.core.exceptions import SentinelError

ALLOWED_ACTIONS: frozenset[str] = frozenset({"get_metric_statistics", "list_metrics"})

# Official Glue metric names/dimensions (documented in AWS Glue metrics docs);
# quality="observed" only for data actually returned by the API.
GLUE_NAMESPACE = "Glue"
GLUE_JOB_DIMENSIONS = ("JobName", "JobRunId", "Type")


class CloudWatchMetricsConnector:
    """Fetch metric statistics into MetricObservation records."""

    def __init__(self, session: Any, *, allow_network: bool = True) -> None:
        if not allow_network:
            raise SentinelError(
                code="aws.offline",
                message="perfil offline bloqueia acesso à AWS — analise artefatos locais",
                details={},
            )
        try:
            self._client = session.client("cloudwatch")
        except Exception as exc:
            raise map_client_error(exc, context="criar cliente CloudWatch") from exc

    def _call(self, api: str, **params: Any) -> Any:
        if api not in ALLOWED_ACTIONS:
            raise SentinelError(
                code="aws.acao_nao_permitida",
                message=f"ação '{api}' não está na allowlist read-only do conector",
                details={"api": api},
            )
        try:
            return getattr(self._client, api)(**params)
        except Exception as exc:
            raise map_client_error(exc, context=f"cloudwatch:{api}") from exc

    def get_metric_statistics(
        self,
        *,
        namespace: str,
        metric_name: str,
        dimensions: dict[str, str],
        start: datetime,
        end: datetime,
        period_seconds: int = 60,
        statistics: tuple[str, ...] = ("Average",),
        semantics: str = "gauge",
    ) -> list[MetricObservation]:
        """One metric → ordered observations. Empty when metric absent."""
        resp = self._call(
            "get_metric_statistics",
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=[{"Name": k, "Value": v} for k, v in dimensions.items()],
            StartTime=start,
            EndTime=end,
            Period=period_seconds,
            Statistics=list(statistics),
        )
        out: list[MetricObservation] = []
        for point in sorted(resp.get("Datapoints", []), key=lambda d: d["Timestamp"]):
            for stat in statistics:
                if stat not in point:
                    continue
                out.append(
                    MetricObservation(
                        namespace=namespace,
                        metric_name=metric_name,
                        dimensions=dict(dimensions),
                        timestamp=point["Timestamp"],
                        value=float(point[stat]),
                        unit=str(point.get("Unit", "None")),
                        statistic=stat,
                        source="cloudwatch",
                        quality="observed",
                        semantics=semantics,
                    )
                )
        return out
