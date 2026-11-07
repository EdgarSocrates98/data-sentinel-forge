"""Bare-command home for Data Sentinel."""

from __future__ import annotations

from data_sentinel.ui.kit import UIContext
from data_sentinel.ui.tui import run_tui


def run_home(*, ctx: UIContext | None = None) -> int:
    return run_tui(ctx=ctx)


__all__ = ["run_home"]
