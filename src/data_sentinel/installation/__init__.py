"""Universal installation architecture for Data Sentinel (cycle 08.2).

Pipeline: Discovery -> Capability Check -> Planning -> Preview -> Approval
-> Apply -> Verify -> Receipt. Planning is deterministic: identical inputs
produce an identical ``plan_id`` (content hash).

Nothing in this package mutates host or project state by itself; the
planner emits an :class:`InstallPlan`, the applier (ds-0110) executes it,
and the receipt store (ds-0117) records what was done.
"""

from data_sentinel.installation.contracts import (
    ComponentKind,
    GatewayProfile,
    InstallChange,
    InstallPlan,
    InstallProfile,
    InstallReceipt,
    InstallScope,
    ManagedFile,
    PlannedAction,
)

__all__ = [
    "ComponentKind",
    "GatewayProfile",
    "InstallChange",
    "InstallPlan",
    "InstallProfile",
    "InstallReceipt",
    "InstallScope",
    "ManagedFile",
    "PlannedAction",
]
