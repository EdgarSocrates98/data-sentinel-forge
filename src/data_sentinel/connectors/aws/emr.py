"""Read-only EMR on EC2 connector (ds-0061, §3.1/§13.1).

Allowlist emr:* read-only — ListClusters, DescribeCluster, ListSteps,
DescribeStep, ListInstanceGroups, ListInstanceFleets, ListInstances,
ListBootstrapActions. No mutating call is reachable.
"""

from __future__ import annotations

import time
from typing import Any

from data_sentinel.connectors.aws.errors import map_client_error
from data_sentinel.core.exceptions import SentinelError

ALLOWED_ACTIONS: frozenset[str] = frozenset({
    "list_clusters", "describe_cluster", "list_steps",
    "describe_step", "list_instance_groups",
    "list_instance_fleets", "list_instances",
    "list_bootstrap_actions",
})

_RETRYABLE = frozenset({"ThrottlingException", "TooManyRequestsException"})


class EmrConnector:
    """Single-funnel read-only EMR client."""

    def __init__(self, session: Any, *,
                 allow_network: bool = True,
                 max_retries: int = 4,
                 backoff_base: float = 0.5) -> None:
        if not allow_network:
            raise SentinelError(
                code="aws.offline",
                message="perfil offline bloqueia acesso à AWS",
                details={})
        self._client = None
        self._max_retries = max_retries
        self._backoff = backoff_base
        try:
            self._client = session.client("emr")
        except Exception as exc:
            raise map_client_error(
                exc, context="criar cliente EMR") from exc

    def _call(self, api: str, **params: Any) -> dict[str, Any]:
        if api not in ALLOWED_ACTIONS:
            raise SentinelError(
                code="aws.acao_nao_permitida",
                message=f"ação '{api}' fora da allowlist EMR read-only",
                details={"api": api,
                         "allowed": sorted(ALLOWED_ACTIONS)})
        attempt = 0
        while True:
            try:
                out: dict[str, Any] = getattr(
                    self._client, api)(**params)
                return out
            except Exception as exc:
                code = str(getattr(exc, "response", {})
                           .get("Error", {}).get("Code", ""))
                if code in _RETRYABLE and attempt < self._max_retries:
                    time.sleep(self._backoff * (2 ** attempt))
                    attempt += 1
                    continue
                raise map_client_error(
                    exc, context=f"emr:{api}") from exc

    def describe_cluster(self, cluster_id: str) -> dict[str, Any]:
        return self._call("describe_cluster", ClusterId=cluster_id)

    def list_steps(self, cluster_id: str) -> dict[str, Any]:
        return self._call("list_steps", ClusterId=cluster_id)

    def describe_step(self, cluster_id: str, step_id: str
                      ) -> dict[str, Any]:
        return self._call("describe_step", ClusterId=cluster_id,
                          StepId=step_id)

    def list_instance_groups(self, cluster_id: str
                             ) -> dict[str, Any]:
        return self._call("list_instance_groups",
                          ClusterId=cluster_id)

    def list_instance_fleets(self, cluster_id: str) -> dict[str, Any]:
        return self._call("list_instance_fleets",
                          ClusterId=cluster_id)

    def list_bootstrap_actions(self, cluster_id: str
                               ) -> dict[str, Any]:
        return self._call("list_bootstrap_actions",
                          ClusterId=cluster_id)
