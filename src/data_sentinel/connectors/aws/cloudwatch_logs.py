"""Read-only CloudWatch Logs connector (§4.1).

Never assumes a fixed Glue log group — group/stream are explicit inputs.
Volume is capped; raw logs are returned, not persisted by the connector.
"""

from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

from data_sentinel.connectors.aws.errors import map_client_error
from data_sentinel.connectors.aws.models import LogEvent
from data_sentinel.core.exceptions import SentinelError

ALLOWED_ACTIONS: frozenset[str] = frozenset(
    {
        "get_log_events",
        "filter_log_events",
        "describe_log_streams",
    }
)


class CloudWatchLogsConnector:
    """Read CloudWatch log events with pagination, windows and caps."""

    def __init__(
        self, session: Any, *, allow_network: bool = True, max_events: int = 10_000
    ) -> None:
        if not allow_network:
            raise SentinelError(
                code="aws.offline",
                message="perfil offline bloqueia acesso à AWS — analise artefatos locais",
                details={},
            )
        self._max_events = max_events
        try:
            self._client = session.client("logs")
        except Exception as exc:
            raise map_client_error(exc, context="criar cliente CloudWatch Logs") from exc

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
            raise map_client_error(exc, context=f"logs:{api}") from exc

    def get_log_events(
        self,
        *,
        group: str,
        stream: str,
        start_ms: int | None = None,
        end_ms: int | None = None,
        limit: int | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> Iterator[LogEvent]:
        """Yield events oldest→newest, paginated, capped at max_events."""
        cap = min(limit or self._max_events, self._max_events)
        params: dict[str, Any] = {
            "logGroupName": group,
            "logStreamName": stream,
            "limit": min(10_000, cap),
        }
        if start_ms is not None:
            params["startTime"] = start_ms
        if end_ms is not None:
            params["endTime"] = end_ms
        yielded = 0
        token: str | None = None
        while yielded < cap:
            if cancelled is not None and cancelled():
                return
            if token:
                params["nextToken"] = token
            resp = self._call("get_log_events", **params)
            events = resp.get("events", [])
            if not events:
                return
            for ev in events:
                if yielded >= cap or (cancelled is not None and cancelled()):
                    return
                yield LogEvent(
                    group=group,
                    stream=stream,
                    timestamp=datetime.fromtimestamp(ev["timestamp"] / 1000).astimezone(),
                    message=str(ev.get("message", "")),
                )
                yielded += 1
            token = resp.get("nextForwardToken")
            if not token:
                return

    def filter_log_events(
        self,
        *,
        group: str,
        filter_pattern: str = "",
        streams: list[str] | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        limit: int | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> Iterator[LogEvent]:
        """Server-side filtered events across streams (e.g., by run id)."""
        cap = min(limit or self._max_events, self._max_events)
        params: dict[str, Any] = {"logGroupName": group, "limit": min(10_000, cap)}
        if filter_pattern:
            params["filterPattern"] = filter_pattern
        if streams:
            params["logStreamNames"] = streams[:100]
        if start_ms is not None:
            params["startTime"] = start_ms
        if end_ms is not None:
            params["endTime"] = end_ms
        yielded = 0
        token: str | None = None
        while yielded < cap:
            if cancelled is not None and cancelled():
                return
            if token:
                params["nextToken"] = token
            resp = self._call("filter_log_events", **params)
            events = resp.get("events", [])
            if not events:
                return
            for ev in events:
                if yielded >= cap or (cancelled is not None and cancelled()):
                    return
                yield LogEvent(
                    group=group,
                    stream=str(ev.get("logStreamName", "")),
                    timestamp=datetime.fromtimestamp(ev["timestamp"] / 1000).astimezone(),
                    message=str(ev.get("message", "")),
                )
                yielded += 1
            token = resp.get("nextToken")
            if not token:
                return
