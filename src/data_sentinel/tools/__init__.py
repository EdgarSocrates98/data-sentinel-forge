"""Tool registry (ds-0052, §5.1-§5.2).

Wraps existing deterministic analyzers as first-class, contract-bound
tools. Same services the CLI uses — no duplicated rules.
"""

from data_sentinel.tools.registry import (
    ToolRegistry,
    ToolUnavailableError,
    build_default_registry,
    execute_tool,
)

__all__ = [
    "ToolRegistry",
    "ToolUnavailableError",
    "build_default_registry",
    "execute_tool",
]
