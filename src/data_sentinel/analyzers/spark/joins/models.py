"""Join intelligence models (§6).

Cardinality reasoning is evidence-based: declared/estimated statistics are
labeled, real cardinality is never derived from row counts alone, and
missing evidence produces explicit missing-evidence lists — not guesses.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class JoinForm(StrEnum):
    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FULL = "FULL"
    CROSS = "CROSS"
    SEMI = "SEMI"
    ANTI = "ANTI"
    OTHER = "OTHER"


class UniquenessState(StrEnum):
    KNOWN_UNIQUE = "known_unique"  # declared/observed evidence of uniqueness
    KNOWN_NON_UNIQUE = "known_non_unique"  # evidence of duplicates
    UNKNOWN = "unknown"  # no evidence either way
    VIOLATED = "violated"  # declared unique but observed duplicates


@dataclass
class KeyStats:
    column: str
    distinct: int | None = None
    null_fraction: float | None = None
    source: str = "declared"  # declared | estimated | observed


@dataclass
class TableStats:
    name: str
    row_count: int | None = None
    keys: dict[str, KeyStats] = field(default_factory=dict)
    top_keys: list[dict[str, float | str]] = field(default_factory=list)
    source: str = "declared"


@dataclass
class JoinSide:
    table: str
    keys: list[str] = field(default_factory=list)
    row_count: int | None = None
    uniqueness: UniquenessState = UniquenessState.UNKNOWN
    stats_source: str = "unavailable"  # declared | estimated | observed | unavailable


@dataclass
class JoinSignature:
    join_id: str
    form: JoinForm
    left: JoinSide
    right: JoinSide
    condition: str  # raw ON text or plan expression
    equality_keys: list[tuple[str, str]] = field(default_factory=list)
    is_inequality: bool = False
    is_expression_based: bool = False
    source: str = "sql"  # sql | plan
    source_span: tuple[int, int] = (0, 0)


@dataclass
class CardinalityAssessment:
    join_id: str
    estimated_output: str  # numeric string labeled, or "unavailable"
    estimate_basis: str  # estimated_from_declared | unavailable
    fan_out: str  # none | right | left | both | unknown
    many_to_many_risk: bool
    expansion_ratio: str  # ratio string or "unavailable"
    missing_evidence: list[str] = field(default_factory=list)
    stats_to_collect: list[str] = field(default_factory=list)


class SkewKind(StrEnum):
    SUSPECTED = "suspected"  # inferred from declared stats/patterns
    OBSERVED = "observed"  # operational metrics evidence


@dataclass
class SkewSignal:
    kind: SkewKind
    target: str  # stage/node/table — never claims a key from stage metrics
    detail: str
    basis: str


@dataclass
class JoinRecommendation:
    recommendation_id: str
    target: str
    prerequisites: list[str]
    evidence_ids: list[str]
    semantic_risk: str
    expected_benefit: str  # always labeled hypothesis
    validation_method: str
    rollback: str
