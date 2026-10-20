"""Operational lineage ingestion (ds-0044, §6).

Parses OpenLineage run events preserving provenance and distinguishing
declared (static) vs observed (runtime) lineage.
"""

from data_sentinel.lineage.openlineage import (
    IngestedLineage,
    parse_openlineage_events,
)

__all__ = ["IngestedLineage", "parse_openlineage_events"]
