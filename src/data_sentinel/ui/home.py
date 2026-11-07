"""Bare-command home for Data Sentinel."""

from __future__ import annotations

from data_sentinel.ui.kit import NonInteractive, UIContext
from data_sentinel.ui.tui import run_tui


def run_home(*, ctx: UIContext | None = None) -> int:
    if ctx is not None and not ctx.interactive:
        raise NonInteractive("Data Sentinel home requires a TTY")
    return run_tui(ctx=ctx)


__all__ = ["run_home"]
