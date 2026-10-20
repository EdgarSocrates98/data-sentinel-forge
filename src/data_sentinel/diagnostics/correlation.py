"""Error correlation heuristics (§4.3).

Deterministic, documented rules — no ML. Distinguishes the primary error
from secondary/cascade errors so a root executor OOM does not make every
subsequent stage failure look like an independent root cause.

Rules (in order):
1. Exceptions arriving via "Caused by:"/Suppressed are chained — attached
   to the exception above them, never promoted to primary.
2. The first non-chained exception in chronological order is the primary
   candidate.
3. Later exceptions are secondary when they are stage/task/executor
   downstream signals (TaskKilled, stage failed, ExecutorLostFailure)
   OR appear within `window_seconds` after the primary — plausible cascade.
4. A later *independent* exception class outside the window and not
   chained may open a new incident group.
"""

from dataclasses import dataclass, field

from data_sentinel.analyzers.cloudwatch.log_parser import ParsedEvent, ParsedLog

CASCADE_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "TaskKilled",
        "TaskKilledException",
        "FetchFailedException",  # downstream shuffle loss after executor dies
    }
)

_CASCADE_TEXT = frozenset(("stage failed", "job aborted", "task killed"))


@dataclass
class Incident:
    """A correlated incident: one primary error + its cascade."""

    primary: ParsedEvent | None
    secondary: list[ParsedEvent] = field(default_factory=list)
    all_events: list[ParsedEvent] = field(default_factory=list)

    @property
    def secondary_count(self) -> int:
        return len(self.secondary)


@dataclass
class CorrelationResult:
    incidents: list[Incident]
    total_exceptions: int
    chained_count: int


def _is_cascade(event: ParsedEvent) -> bool:
    if event.exception_class in CASCADE_EXCEPTIONS:
        return True
    lower = event.message.lower()
    return any(token in lower for token in _CASCADE_TEXT)


def correlate(parsed: ParsedLog, *, window_seconds: float = 300.0) -> CorrelationResult:
    """Group parsed events into incidents via the documented rules."""
    events = parsed.exceptions
    incidents: list[Incident] = []
    chained = 0
    current: Incident | None = None

    for event in events:
        if event.is_chained:
            chained += 1
            if current is not None:
                current.secondary.append(event)
                current.all_events.append(event)
            else:
                # orphaned "Caused by" — still a real root signature
                current = Incident(primary=event, all_events=[event])
                incidents.append(current)
            continue
        if current is None or current.primary is None:
            current = Incident(primary=event, all_events=[event])
            incidents.append(current)
            continue
        within_window = (
            event.timestamp is not None
            and current.primary.timestamp is not None
            and abs((event.timestamp - current.primary.timestamp).total_seconds())
            <= window_seconds
        )
        if _is_cascade(event) or within_window:
            current.secondary.append(event)
            current.all_events.append(event)
        else:
            current = Incident(primary=event, all_events=[event])
            incidents.append(current)

    if current is None and parsed.events:
        # no exceptions at all — single incident with no primary
        incidents.append(Incident(primary=None, all_events=list(parsed.events)))

    return CorrelationResult(
        incidents=incidents,
        total_exceptions=len(events),
        chained_count=chained,
    )
