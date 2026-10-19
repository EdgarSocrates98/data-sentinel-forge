"""Configuration models, profiles, and precedence layers (§01.5, §6)."""

import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from data_sentinel.core.contracts.enums import AnalysisMode

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
OutputFormat = Literal["text", "json"]

_ENV_PREFIX = "DATA_SENTINEL_"

_SECRET_KEY = re.compile(
    r"(?i)(secret|password|passwd|token|api[_-]?key|access[_-]?key|"
    r"private[_-]?key|credential|authorization|session[_-]?key)"
)

REDACTED = "***REDACTED***"


@dataclass(frozen=True)
class ProfileLimits:
    """Per-profile resource limits. Budgets are Cycle 05 placeholders."""

    max_file_bytes: int
    max_evidence_excerpt_chars: int
    allow_network: bool
    token_budget: int | None = None  # reserved for Cycle 05 (LLM budgets)
    tool_call_budget: int | None = None  # reserved for Cycle 05


PROFILES: dict[AnalysisMode, ProfileLimits] = {
    AnalysisMode.ECONOMY: ProfileLimits(
        max_file_bytes=10 * 1024 * 1024,
        max_evidence_excerpt_chars=2_000,
        allow_network=True,
    ),
    AnalysisMode.BALANCED: ProfileLimits(
        max_file_bytes=50 * 1024 * 1024,
        max_evidence_excerpt_chars=8_000,
        allow_network=True,
    ),
    AnalysisMode.DEEP: ProfileLimits(
        max_file_bytes=200 * 1024 * 1024,
        max_evidence_excerpt_chars=32_000,
        allow_network=True,
    ),
    AnalysisMode.OFFLINE: ProfileLimits(
        max_file_bytes=50 * 1024 * 1024,
        max_evidence_excerpt_chars=8_000,
        allow_network=False,
    ),
}


class ConfigSource(BaseModel):
    """Provenance of a configuration layer."""

    layer: Literal["cli", "env", "project", "user", "default"]
    path: str | None = None
    found: bool = False
    applied: bool = False


class SentinelConfig(BaseModel):
    """Resolved runtime configuration.

    ``None`` on a limit field means "use the active profile's default".
    Unknown keys are tolerated (forward compatibility) and still redacted
    by :meth:`to_redacted_dict` when they look secret.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    profile: AnalysisMode = AnalysisMode.BALANCED
    log_level: LogLevel = "INFO"
    output_format: OutputFormat = "text"
    max_file_bytes: int | None = Field(default=None, gt=0)
    max_evidence_excerpt_chars: int | None = Field(default=None, gt=0)
    redact_secrets: bool = True
    store_path: str = "~/.local/share/data-sentinel"
    allowed_roots: list[str] = Field(default_factory=list)
    sources: list[ConfigSource] = Field(default_factory=list)

    def effective_limits(self) -> ProfileLimits:
        """Profile defaults merged with explicit overrides (offline is absolute)."""
        base = PROFILES[self.profile]
        return ProfileLimits(
            max_file_bytes=self.max_file_bytes or base.max_file_bytes,
            max_evidence_excerpt_chars=(
                self.max_evidence_excerpt_chars or base.max_evidence_excerpt_chars
            ),
            allow_network=base.allow_network,
            token_budget=base.token_budget,
            tool_call_budget=base.tool_call_budget,
        )

    def to_redacted_dict(self) -> dict[str, Any]:
        """model_dump with every secret-looking key (known or extra) redacted."""
        return _redact_mapping(self.model_dump(mode="json"))

    def __repr__(self) -> str:
        return f"SentinelConfig({self.to_redacted_dict()!r})"


def _redact_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in mapping.items():
        if _SECRET_KEY.search(str(key)):
            out[key] = REDACTED
        elif isinstance(value, dict):
            out[key] = _redact_mapping(value)
        elif isinstance(value, list):
            out[key] = [
                _redact_mapping(v) if isinstance(v, dict) else v for v in value
            ]
        else:
            out[key] = value
    return out


def env_field_name(env_name: str) -> str | None:
    """Map DATA_SENTINEL_* env var to a SentinelConfig field name."""
    if not env_name.startswith(_ENV_PREFIX):
        return None
    return env_name[len(_ENV_PREFIX) :].lower()
