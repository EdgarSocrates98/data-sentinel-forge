"""Domain exceptions with structured error information."""

from typing import Any


class SentinelError(Exception):
    """Base error carrying a stable code, a message, and optional details."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details: dict[str, Any] = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


class ContractValidationError(SentinelError):
    """A public contract failed to parse or validate."""


class ConfigurationError(SentinelError):
    """Configuration loading or validation failed."""


class InputValidationError(SentinelError):
    """User-supplied input is invalid or unsafe to process."""


class SecurityViolationError(SentinelError):
    """A request violated a security guard (paths, secrets, limits)."""


class PathViolationError(SecurityViolationError):
    """A file path resolved outside the allowed roots."""


class AnalyzerError(SentinelError):
    """An analyzer failed to complete its deterministic pass."""


class PersistenceError(SentinelError):
    """Local persistence (storage, migrations) failed."""
