"""Secret redaction for evidence excerpts (§01.7, §10).

Conservative by design: prefer over-masking near-certain secrets over
leaking. Markers are stable and self-describing (``«redacted:<kind>»``).
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretPattern:
    kind: str
    regex: re.Pattern[str]
    replacement: str

    def apply(self, text: str) -> str:
        return self.regex.sub(self.replacement, text)


SECRET_PATTERNS: tuple[SecretPattern, ...] = (
    SecretPattern(
        "private-key",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        "«redacted:private-key»",
    ),
    SecretPattern(
        "connection-string-credentials",
        re.compile(r"\b([a-zA-Z][a-zA-Z0-9+.-]*://)[^:\s/@'\"]+:[^@\s'\"]+@"),
        r"\1«redacted:credentials»@",
    ),
    SecretPattern(
        "aws-access-key-id",
        re.compile(r"\b(?:AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}\b"),
        "«redacted:aws-access-key-id»",
    ),
    SecretPattern(
        "aws-secret-key",
        re.compile(
            r"(?i)\b((?:aws_)?secret(?:_access)?_key|aws_secret_access_key)"
            r"(\s*[=:]\s*['\"]?)[A-Za-z0-9/+=]{20,}"
        ),
        r"\1\2«redacted:aws-secret-key»",
    ),
    SecretPattern(
        "bearer-token",
        re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{10,}"),
        "«redacted:bearer-token»",
    ),
    SecretPattern(
        "authorization-header",
        re.compile(
            r"(?i)\b(authorization\s*[=:]\s*)"
            r"(?:(?:basic|bearer|digest|token|aws4-hmac-sha256)\s+)?[^\s'\"«»]+"
        ),
        r"\1«redacted:authorization»",
    ),
    SecretPattern(
        "well-known-token",
        re.compile(
            r"\b(?:xox[baprs]-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}|"
            r"github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,})\b"
        ),
        "«redacted:token»",
    ),
    SecretPattern(
        "key-value-secret",
        re.compile(
            r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|"
            r"session[_-]?key|private[_-]?key|authorization)"
            r"(\s*[=:]\s*)(['\"]?)[^\s'\",}«»]{4,}\3"
        ),
        r"\1\2«redacted:secret»",
    ),
)


def redact_secrets(text: str) -> str:
    """Apply every secret pattern, in order, to ``text``."""
    for pattern in SECRET_PATTERNS:
        text = pattern.apply(text)
    return text
