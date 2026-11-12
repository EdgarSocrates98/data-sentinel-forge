"""Data Sentinel → Obsidian quality review projection.

Composes a sanitized ``theforge/ObsidianNoteRef/v1`` note for data-quality
and contract scans.  Projection only — the vendored
``data_sentinel._forge_obsidian`` engine owns vault bytes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from data_sentinel._forge_obsidian.notes import build_note_ref, section_yaml

FORGE_ID = "data-sentinel-forge"


def build_obsidian_quality_review(
    *,
    title: str,
    summary: str,
    workspace: str,
    vault_id: str,
    checks: Iterable[Mapping[str, Any]] | None = None,
    violations: Iterable[Mapping[str, Any]] | None = None,
    evidence: Iterable[Mapping[str, Any]] | None = None,
    related_refs: Iterable[str] | None = None,
    note_path: str | None = None,
    confidence: str = "unknown",
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose a data quality review note (checks + violations + evidence)."""
    return build_note_ref(
        forge_id=FORGE_ID,
        title=title,
        summary=summary,
        workspace=workspace,
        vault_id=vault_id,
        kind="quality-review",
        body_sections=[
            section_yaml("Checks", list(checks or [])),
            section_yaml("Violations", list(violations or [])),
            section_yaml("Evidence", list(evidence or [])),
        ],
        note_path=note_path,
        confidence=confidence,
        tags=["data", "sentinel", "quality"],
        related=list(related_refs or []),
        provenance=provenance,
    )


__all__ = ["FORGE_ID", "build_obsidian_quality_review"]
