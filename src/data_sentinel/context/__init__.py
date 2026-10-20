"""Context engineering (ds-0054, §6).

Layered context assembly with evidence preservation, a bounded cache,
and a token economy tracker. Deterministic; no LLM required.
"""

from data_sentinel.context.budget import TokenBudget, estimate_tokens
from data_sentinel.context.cache import ContextCache
from data_sentinel.context.layers import (
    ContextLayer,
    LayeredContext,
    build_context,
)

__all__ = [
    "ContextCache",
    "ContextLayer",
    "LayeredContext",
    "TokenBudget",
    "build_context",
    "estimate_tokens",
]
