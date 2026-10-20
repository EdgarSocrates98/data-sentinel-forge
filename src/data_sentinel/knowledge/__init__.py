"""Deterministic compatibility knowledge base (Cycle 03)."""

from data_sentinel.knowledge.engine import RuleMatch, select
from data_sentinel.knowledge.schema import (
    Rule,
    RuleValidationError,
    load_packaged_rules,
    load_rules,
    validate_rule,
)

__all__ = [
    "Rule",
    "RuleMatch",
    "RuleValidationError",
    "load_packaged_rules",
    "load_rules",
    "select",
    "validate_rule",
]
