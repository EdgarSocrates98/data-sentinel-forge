"""Forge UI Kit — stdlib-only interactive terminal layer (vendored from
spark-forge-aws; byte-adapted for data_sentinel imports).

Zero dependencies, cross-platform (msvcrt on Windows, termios on
POSIX). Every interaction has a headless equivalent so automation never
blocks on a TTY that isn't there.
"""

from data_sentinel.ui.i18n import t
from data_sentinel.ui.kit import (
    UIContext,
    confirm,
    dashboard,
    multi_select,
    prompt,
    select,
    status_table,
)

__all__ = [
    "UIContext",
    "confirm",
    "dashboard",
    "multi_select",
    "prompt",
    "select",
    "status_table",
    "t",
]
