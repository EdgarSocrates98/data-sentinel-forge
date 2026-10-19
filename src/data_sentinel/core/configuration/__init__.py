"""Configuration system with documented precedence (§01.5)."""

from data_sentinel.core.configuration.loader import (
    PROJECT_CONFIG_NAME,
    USER_CONFIG_NAME,
    load_config,
)
from data_sentinel.core.configuration.models import (
    PROFILES,
    REDACTED,
    ConfigSource,
    LogLevel,
    OutputFormat,
    ProfileLimits,
    SentinelConfig,
)

__all__ = [
    "PROFILES",
    "PROJECT_CONFIG_NAME",
    "REDACTED",
    "USER_CONFIG_NAME",
    "ConfigSource",
    "LogLevel",
    "OutputFormat",
    "ProfileLimits",
    "SentinelConfig",
    "load_config",
]
