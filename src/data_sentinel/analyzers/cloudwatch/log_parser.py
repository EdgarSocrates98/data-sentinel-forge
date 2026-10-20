"""CloudWatch log event parser (§4.2).

Extracts structured ParsedEvent records from log text — timestamps,
exception classes, chained-exception markers — preserving message + stack
context. Unknown lines stay unparsed but timestamped when a timestamp
prefix exists.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

# Known JVM/Spark/Glue exception signatures (examples from §4.2, extensible).
KNOWN_EXCEPTIONS: tuple[str, ...] = (
    "Py4JJavaError",
    "SparkException",
    "AnalysisException",
    "OutOfMemoryError",
    "ExecutorLostFailure",
    "FetchFailedException",
    "TaskKilledException",
    "TaskKilled",
    "PermissionDeniedException",
    "AccessDeniedException",
    "AmazonS3Exception",
    "S3Exception",
    "GlueCatalogException",
    "EntityNotFoundException",
    "IcebergException",
    "ParseException",
    "SQLException",
    "AmazonClientException",
)

_EXC_RE = re.compile(
    r"(?:^|[\s(])(?P<exc>(?:[\w.]+\.)?(?:" + "|".join(KNOWN_EXCEPTIONS) + r"))[\s:(]"
)
_TS_RE = re.compile(
    r"^(?P<ts>\d{2,4}[-/]\d{2}[-/]\d{2,4}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)"
)
_ISO_RE = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)")
_CAUSED_RE = re.compile(r"^\s*(Caused by:|Suppressed:)", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedEvent:
    """One parsed log line (or block) with optional structure."""

    line_no: int
    timestamp: datetime | None
    exception_class: str | None
    is_chained: bool  # "Caused by:"/suppressed line
    message: str
    raw: str


@dataclass
class ParsedLog:
    """Result of parsing a log text."""

    events: list[ParsedEvent] = field(default_factory=list)
    exceptions: list[ParsedEvent] = field(default_factory=list)
    unparsed_lines: int = 0


def parse_timestamp(text: str) -> datetime | None:
    """Best-effort timestamp extraction — real prefixes only."""
    for regex in (_ISO_RE, _TS_RE):
        m = regex.match(text)
        if not m:
            continue
        raw = m.group("ts").split(".")[0].rstrip("Z").replace("T", " ").replace(",", "")
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ):
            try:
                return datetime.strptime(raw[:19], fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
    return None


def parse_log_text(text: str) -> ParsedLog:
    """Parse multi-line log text into structured events."""
    result = ParsedLog()
    for idx, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        ts = parse_timestamp(line)
        chained = bool(_CAUSED_RE.match(line))
        exc_match = _EXC_RE.search(line)
        exc_class = exc_match.group("exc").split(".")[-1] if exc_match else None
        if ts is None and exc_class is None and not chained:
            result.unparsed_lines += 1
        event = ParsedEvent(
            line_no=idx,
            timestamp=ts,
            exception_class=exc_class,
            is_chained=chained,
            message=line.strip(),
            raw=line,
        )
        result.events.append(event)
        if exc_class:
            result.exceptions.append(event)
    return result
