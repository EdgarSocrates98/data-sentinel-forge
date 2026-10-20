"""Control Center API — real FastAPI surface over the Sentinel core (ds-0071).

No diagnostic logic lives in endpoints: every route delegates to the
existing registry, analyzers, tool registry, or investigator.
"""

from .app import create_app

__all__ = ["create_app"]
