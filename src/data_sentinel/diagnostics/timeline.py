"""Incident timeline (§4.6).

Chronological event sequence — every entry carries a timestamp actually
observed in the input; undated lines are summarized separately, never
assigned invented times.
"""

from dataclasses import dataclass, field
from datetime import datetime

from data_sentinel.analyzers.cloudwatch.log_parser import ParsedLog

_MAX_SUMMARY = 80


@dataclass(frozen=True)
class TimelineEntry:
    timestamp: datetime  # always observed, never synthesized
    summary: str
    exception_class: str | None
    line_no: int


@dataclass
class IncidentTimeline:
    entries: list[TimelineEntry] = field(default_factory=list)
    undated_lines: int = 0

    def render(self) -> str:
        """PT-BR terminal rendering like the §4.6 example."""
        out: list[str] = []
        for e in self.entries:
            ts = e.timestamp.strftime("%H:%M:%S") if hasattr(e.timestamp, "strftime") else "?"
            out.append(f"{ts} — {e.summary}")
        if self.undated_lines:
            out.append(f"(… {self.undated_lines} linha(s) sem timestamp)")
        return "\n".join(out)


def build_timeline(
    parsed: ParsedLog,
    *,
    only_exceptions: bool = False,
    max_entries: int = 100,
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
            )
        )
    return timeline
