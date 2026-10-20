"""Sentinel Watch — bounded local monitoring & alerting (ds-0084, §5).

Local scheduler only; cloud polling is opt-in and env-gated.
"""

from .engine import Alert, AlertEngine, WatchDefinition, WatchRuntime

__all__ = ["Alert", "AlertEngine", "WatchDefinition", "WatchRuntime"]
