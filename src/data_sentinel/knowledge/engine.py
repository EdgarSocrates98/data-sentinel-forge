"""Rule engine — deterministic selection with conflict detection (§8.2).

Selection: match all declared keys → most specific wins → ties/conflicts
are surfaced, never silently resolved → no match falls back to UNKNOWN.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from data_sentinel.core.contracts.enums import SupportStatus
from data_sentinel.knowledge.schema import Rule


@dataclass
class RuleMatch:
    rule: Rule | None
    status: SupportStatus
    conflicts: list[str] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)


def select(rules: list[Rule], ctx: Mapping[str, str]) -> RuleMatch:
    """Pick the winning rule for a context. Deterministic:

    1. keep rules whose declared keys all match;
    2. keep only the highest specificity;
    3. >1 candidate at same specificity = conflict (reported, status of the
       most conservative candidate is NOT assumed — result is UNKNOWN);
    4. zero candidates → UNKNOWN fallback.
    """
    matched = [r for r in rules if r.matches(dict(ctx))]
    if not matched:
        return RuleMatch(rule=None, status=SupportStatus.UNKNOWN)
    top = max(r.specificity for r in matched)
    best = [r for r in matched if r.specificity == top]
    if len(best) > 1:
        return RuleMatch(
            rule=None,
            status=SupportStatus.UNKNOWN,
            conflicts=[
                f"conflito: regras {sorted(r.rule_id for r in best)} "
                "empatam em especificidade para o contexto"
            ],
            candidates=[r.rule_id for r in best],
        )
    return RuleMatch(rule=best[0], status=best[0].status)
