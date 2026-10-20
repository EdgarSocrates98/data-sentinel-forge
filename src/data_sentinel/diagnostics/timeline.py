"""Incident timeline (§4.6, §4.3-cycle-03.1).

Chronological event sequence — every entry carries a timestamp actually
observed in the input; undated lines are summarized separately, never
assigned invented times. Multi-source timelines declare their granularity
gaps explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from itertools import pairwise
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from data_sentinel.analyzers.cloudwatch.log_parser import ParsedLog

_MAX_SUMMARY = 80
_GAP_SECONDS = 120.0  # >2min between observed events = declared gap


class EventKind(StrEnum):
    EXECUTION_START = "execution_start"
    STAGE = "stage"
    WARNING = "warning"
    EXCEPTION = "exception"
    STATUS_CHANGE = "status_change"
    FAILURE = "failure"
    END = "end"
    GENERIC = "generic"


@dataclass(frozen=True)
class TimelineEntry:
    timestamp: datetime  # always observed, never synthesized
    summary: str
    exception_class: str | None
    line_no: int
    kind: EventKind = EventKind.GENERIC
    source: str = ""  # e.g. "cloudwatch-log", "doctor-bundle"


@dataclass(frozen=True)
class TimelineGap:
    after: datetime
    before: datetime
    seconds: float


@dataclass
class IncidentTimeline:
    entries: list[TimelineEntry] = field(default_factory=list)
    undated_lines: int = 0
    gaps: list[TimelineGap] = field(default_factory=list)
    granularity_notes: list[str] = field(default_factory=list)

    def detect_gaps(self, threshold: float = _GAP_SECONDS) -> list[TimelineGap]:
        """Explicit gaps between consecutive observed timestamps."""
        self.gaps = []
        ordered = sorted(e.timestamp for e in self.entries)
        for a, b in pairwise(ordered):
            delta = (b - a).total_seconds()
            if delta > threshold:
                self.gaps.append(TimelineGap(after=a, before=b, seconds=delta))
        return self.gaps

    def render(self) -> str:
        """PT-BR terminal rendering like the §4.6 example."""
        out: list[str] = []
        prev: datetime | None = None
        gap_set = {(g.after, g.before) for g in self.gaps}
        for e in self.entries:
            if prev is not None and any(
                g[0] == prev and g[1] == e.timestamp for g in gap_set
            ):
                delta = (e.timestamp - prev).total_seconds()
                out.append(f"     — gap de {delta:.0f}s sem eventos observados —")
            ts = e.timestamp.strftime("%H:%M:%S") if hasattr(e.timestamp, "strftime") else "?"
            out.append(f"{ts} — {e.summary}")
            prev = e.timestamp
        if self.undated_lines:
            out.append(f"(… {self.undated_lines} linha(s) sem timestamp)")
        for note in self.granularity_notes:
            out.append(f"(granularidade: {note})")
        return "\n".join(out)


def _classify(event_message: str, exception_class: str | None) -> EventKind:
    m = event_message.lower()
    if exception_class:
        return EventKind.EXCEPTION
    if "warn" in m:
        return EventKind.WARNING
    if "failed" in m or "error" in m:
        return EventKind.FAILURE
    if "stage" in m:
        return EventKind.STAGE
    return EventKind.GENERIC


def build_timeline(
    parsed: ParsedLog,
    *,
    only_exceptions: bool = False,
    max_entries: int = 100,
    source: str = "cloudwatch-log",
) -> IncidentTimeline:
    """Build the timeline from parsed events — real timestamps only."""
    timeline = IncidentTimeline()
    dated = [e for e in parsed.events if e.timestamp is not None]
    timeline.undated_lines = len(parsed.events) - len(dated)
    if only_exceptions:
        dated = [e for e in dated if e.exception_class]
    for event in sorted(dated, key=lambda e: (e.timestamp or e.line_no, e.line_no))[
        :max_entries
    ]:
        if event.timestamp is None:
            continue
        summary = event.message[:_MAX_SUMMARY]
        timeline.entries.append(
            TimelineEntry(
                timestamp=event.timestamp,
                summary=summary,
                exception_class=event.exception_class,
                line_no=event.line_no,
                kind=_classify(event.message, event.exception_class),
                source=source,
            )
        )
    timeline.detect_gaps()
    return timeline


def merge_timelines(*timelines: IncidentTimeline) -> IncidentTimeline:
    """Merge multi-source timelines, keeping per-source granularity honest."""
    merged = IncidentTimeline()
    sources: set[str] = set()
    for tl in timelines:
        merged.entries.extend(tl.entries)
        merged.undated_lines += tl.undated_lines
        merged.granularity_notes.extend(tl.granularity_notes)
        sources.update(e.source for e in tl.entries if e.source)
    merged.entries.sort(key=lambda e: e.timestamp)
    merged.detect_gaps()
    if len(sources) > 1:
        merged.granularity_notes.append(
            "fontes múltiplas: " + ", ".join(sorted(sources))
        )
    return merged
