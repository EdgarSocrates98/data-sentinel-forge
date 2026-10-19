"""Security primitives: path guard, file-input guard, sanitization, redaction."""

from data_sentinel.core.security.paths import (
    InputFile,
    read_input_file,
    safe_resolve,
)
from data_sentinel.core.security.redact import SECRET_PATTERNS, redact_secrets
from data_sentinel.core.security.sanitize import (
    TRUNCATION_MARKER,
    sanitize_evidence_excerpt,
    sanitize_log_text,
)

__all__ = [
    "SECRET_PATTERNS",
    "TRUNCATION_MARKER",
    "InputFile",
    "read_input_file",
    "redact_secrets",
    "safe_resolve",
    "sanitize_evidence_excerpt",
    "sanitize_log_text",
]
