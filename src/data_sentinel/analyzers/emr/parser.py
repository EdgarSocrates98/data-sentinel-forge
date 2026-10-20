"""EMR on EC2 parsers (§3.1) — offline JSON from exported API calls.

Accepts DescribeCluster / ListSteps / ListInstanceGroups payloads —
either a single call result or {"calls": {...}} bundle. Tolerant to
missing fields; unknown keys preserved, never interpreted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmrClusterDoc:
    cluster: dict[str, Any] = field(default_factory=dict)
    steps: list[dict[str, Any]] = field(default_factory=list)
    instance_groups: list[dict[str, Any]] = field(default_factory=list)
    instance_fleets: list[dict[str, Any]] = field(default_factory=list)
    bootstrap_actions: list[dict[str, Any]] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


_KNOWN = {"Cluster", "Steps", "InstanceGroups", "InstanceFleets",
          "BootstrapActions", "calls", "NextToken", "Marker",
          "ResponseMetadata"}


def parse_cluster(text: str, *, source: str = "") -> EmrClusterDoc:
    doc = EmrClusterDoc()
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        doc.warnings.append(f"{source}: JSON inválido ({exc})")
        return doc
    if not isinstance(raw, dict):
        doc.warnings.append(f"{source}: payload não é objeto")
        return doc

    calls = raw.get("calls", raw)
    if isinstance(calls, dict):
        for key in calls:
            if key not in _KNOWN:
                doc.extras.append(key)
        doc.cluster = calls.get("Cluster", {}) or {}
        doc.steps = _as_list(calls.get("Steps"))
        doc.instance_groups = _as_list(calls.get("InstanceGroups"))
        doc.instance_fleets = _as_list(calls.get("InstanceFleets"))
        doc.bootstrap_actions = _as_list(calls.get("BootstrapActions"))
    else:
        doc.warnings.append("payload sem objeto de calls reconhecível")
    if not doc.cluster and not doc.steps:
        doc.warnings.append(
            "sem Cluster nem Steps — análise será limitada")
    return doc


def parse_steps(text: str) -> list[dict[str, Any]]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return []
    return _as_list(raw.get("Steps") if isinstance(raw, dict) else raw)


def parse_instance_groups(text: str) -> list[dict[str, Any]]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return []
    return _as_list(
        raw.get("InstanceGroups") if isinstance(raw, dict) else raw)


def _as_list(v: Any) -> list[dict[str, Any]]:
    if isinstance(v, list):
        return [x for x in v if isinstance(x, dict)]
    return []
