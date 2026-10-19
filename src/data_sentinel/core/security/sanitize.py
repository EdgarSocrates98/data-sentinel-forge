"""Text sanitization for log/SQL excerpts before they become evidence."""

import re
import unicodedata

from data_sentinel.core.security.redact import redact_secrets

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")

TRUNCATION_MARKER = "... [trecho truncado]"


def sanitize_log_text(text: str, *, max_chars: int | None = None) -> str:
    """Strip ANSI/control sequences, normalize line endings, truncate."""
    text = ANSI_RE.sub("", text)
    text = CONTROL_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    if max_chars is not None and len(text) > max_chars:
        text = text[:max_chars].rstrip() + TRUNCATION_MARKER
    return text


def sanitize_evidence_excerpt(text: str, *, max_chars: int = 8000) -> str:
    """Single entry point analyzers use to build ``Evidence.sanitized_excerpt``.

    Order is deliberate: control characters are stripped first so secret
    patterns see clean text, secrets are redacted next, and only then is
    the excerpt truncated — a secret can never be split at the boundary.
    """
    cleaned = sanitize_log_text(text)
    redacted = redact_secrets(cleaned)
    if len(redacted) > max_chars:
        redacted = redacted[:max_chars].rstrip() + TRUNCATION_MARKER
    return redacted
