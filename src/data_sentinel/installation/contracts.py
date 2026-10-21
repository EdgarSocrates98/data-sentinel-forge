"""Installation contracts (cycle 08.2, prompt §2.2-§2.3).

``InstallPlan`` is the deterministic output of the planner: identical
inputs must produce identical plans (``plan_id`` is a content hash).
``InstallReceipt`` records what was actually applied — it must never
contain secrets (P0, §14).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, Field

INSTALL_SCHEMA_VERSION = "1.0"


class InstallScope(StrEnum):
    """Where installation writes land (§3.2)."""

    PROJECT = "project"  # the current project only
    WORKSPACE = "workspace"  # an explicitly selected workspace root
    USER = "user"  # user-level config, only when the host supports it


class InstallProfile(StrEnum):
    """Component-selection profile (§3.3)."""

    MINIMAL = "minimal"
    RECOMMENDED = "recommended"
    FULL = "full"


class GatewayProfile(StrEnum):
    """Advisory routing/context profile (§3.4).

    Never changes deterministic capabilities or security limits.
    """

    ECONOMY = "economy"
    BALANCED = "balanced"
    DEEP = "deep"


class ComponentKind(StrEnum):
    """Installable component classes (§3.5)."""

    SKILLS = "skills"
    AGENTS = "agents"
    MCP = "mcp"
    HOST_CONFIG = "host-config"
    MARKERS = "markers"
    PORTAL_LAUNCHER = "portal-launcher"


class PlannedAction(StrEnum):
    """What the applier will do to a path."""

    CREATE = "create"
    UPDATE = "update"
    MERGE_JSON = "merge-json"
    SKIP = "skip"
    REFUSE = "refuse"
    BACKUP_UPDATE = "backup-update"


class InstallChange(BaseModel):
    """One planned filesystem/config change."""

    action: PlannedAction
    path: str
    component: ComponentKind
    source_asset: str | None = None
    sha256: str | None = None
    reason: str = ""


class ManagedFile(BaseModel):
    """Ledger entry for a file Sentinel owns (§2.4).

    ``component`` carries the installkit asset kind
    (``skill|agent|mcp|config|marker|state``) — a string, not the
    higher-level :class:`ComponentKind` selection enum.
    """

    path: str
    sha256: str
    component: str
    host: str = ""


class SourceInfo(BaseModel):
    """How the Sentinel package itself was obtained (§8.4)."""

    method: str  # wheel | git | zip | dir | running-repo
    version: str
    integrity: str  # digest of the asset manifest, or "unavailable"


class InstallPlan(BaseModel):
    """Deterministic installation plan (§2.2)."""

    plan_id: str
    schema_version: str = INSTALL_SCHEMA_VERSION
    source: SourceInfo
    scope: InstallScope
    host: str
    profile: InstallProfile
    gateway_profile: GatewayProfile = GatewayProfile.BALANCED
    components: list[ComponentKind]
    target_root: str
    planned_changes: list[InstallChange] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    refusals: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    rollback_plan: list[InstallChange] = Field(default_factory=list)
    created_at: datetime | None = None  # excluded from plan_id hash

    def canonical_payload(self) -> dict[str, Any]:
        """Everything that determines identity — excludes timestamps."""
        data = self.model_dump(mode="json", exclude={"plan_id", "created_at"})
        data["planned_changes"] = sorted(
            data["planned_changes"], key=lambda c: (c["path"], c["action"])
        )
        data["conflicts"] = sorted(data["conflicts"])
        data["refusals"] = sorted(data["refusals"])
        return data

    def compute_plan_id(self) -> str:
        blob = json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class InstallReceipt(BaseModel):
    """Record of an applied installation (§2.3). Never contains secrets."""

    installation_id: str
    plan_id: str
    schema_version: str = INSTALL_SCHEMA_VERSION
    timestamp: datetime
    version: str
    source_method: str
    scope: InstallScope
    host: str
    profile: InstallProfile
    gateway_profile: GatewayProfile = GatewayProfile.BALANCED
    installed_components: list[ComponentKind] = Field(default_factory=list)
    managed_files: list[ManagedFile] = Field(default_factory=list)
    mcp_entries: list[str] = Field(default_factory=list)
    backups: list[str] = Field(default_factory=list)
    validation: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    status: str = "applied"  # applied | partial | failed | rolled-back


RECEIPT_SECRET_KEYS = frozenset(
    {"token", "secret", "password", "key", "credential", "auth"}
)


def assert_no_secrets(receipt: InstallReceipt) -> None:
    """Refuse to persist a receipt whose keys or values look like secrets."""

    import re

    from data_sentinel.core.exceptions import SentinelError

    kv = re.compile(
        r"(?i)\b(?:token|secret|password|credential|api[-_]?key|auth)\b\s*[=:]\s*\S+"
    )

    def _scan(obj: Any, trail: str) -> None:
        if isinstance(obj, dict):
            for key, val in obj.items():
                if any(s in str(key).lower() for s in RECEIPT_SECRET_KEYS):
                    raise SentinelError(
                        code="RECEIPT_SECRET_LEAK",
                        message=f"receipt field {trail}.{key} looks like a secret",
                    )
                _scan(val, f"{trail}.{key}")
        elif isinstance(obj, list):
            for i, val in enumerate(obj):
                _scan(val, f"{trail}[{i}]")
        elif isinstance(obj, str) and kv.search(obj):
            raise SentinelError(
                code="RECEIPT_SECRET_LEAK",
                message=f"receipt value at {trail} looks like a secret",
            )

    _scan(receipt.model_dump(mode="json"), "receipt")


PlanId = Annotated[str, Field(min_length=8)]
