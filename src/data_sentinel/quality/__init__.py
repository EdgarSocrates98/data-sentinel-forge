"""Data quality contracts engine (Cycle 04 §3).

Declarative contract loading/validation — NEVER executes rules against
data (that's observation territory, adapters ds-0042+).
"""

from data_sentinel.quality.adapters import (
    detect_adapter,
    list_adapters,
    normalize,
    parse_ge,
    parse_pydeequ,
)
from data_sentinel.quality.contract import (
    ContractFormatError,
    ContractIssue,
    load_contract,
    parse_contract_text,
    validate_contract,
)
from data_sentinel.quality.versioning import check_version_compat

__all__ = [
    "ContractFormatError",
    "ContractIssue",
    "check_version_compat",
    "detect_adapter",
    "list_adapters",
    "load_contract",
    "normalize",
    "parse_contract_text",
    "parse_ge",
    "parse_pydeequ",
    "validate_contract",
]
