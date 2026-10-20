"""Layered context assembly (§6.1) + evidence preservation (§6.2).

Layers, in priority order:
1. problem — the task at hand
2. evidence — raw findings/observations (PRESERVED, never summarized
   away; truncation marked explicitly)
3. knowledge — retrieved docs/chunks
4. constraints — budgets, policies, limits
5. history — prior observations/decisions

Evidence chunks keep provenance and are truncated with a marker, never
fabricated or silently dropped.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import IntEnum

from data_sentinel.context.budget import TokenBudget, estimate_tokens

MAX_EVIDENCE_CHARS = 4_000


class ContextLayer(IntEnum):
    PROBLEM = 0
    EVIDENCE = 1
    KNOWLEDGE = 2
    CONSTRAINTS = 3
    HISTORY = 4


@dataclass
class ContextChunk:
    layer: ContextLayer
    text: str
    provenance: str = ""
    truncated: bool = False
    tokens: int = 0


@dataclass
class LayeredContext:
    chunks: list[ContextChunk] = field(default_factory=list)
    budget_notes: list[str] = field(default_factory=list)
    total_tokens: int = 0
    digest: str = ""

    def render(self) -> str:
        order = {layer: i for i, layer in enumerate(ContextLayer)}
        parts = []
        for c in sorted(self.chunks, key=lambda c: order[c.layer]):
            marker = f" [truncado:{c.provenance}]" if c.truncated else ""
            prov = f" ({c.provenance})" if c.provenance else ""
            parts.append(f"[{c.layer.name}]{prov}{marker}\n{c.text}")
        if self.budget_notes:
            parts.append("[BUDGET]\n" + "\n".join(self.budget_notes))
        return "\n\n".join(parts)


def _preserve(text: str, limit: int = MAX_EVIDENCE_CHARS) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n…[TRUNCATED — original preserved]", True


def build_context(
    *,
    problem: str,
    evidence: list[tuple[str, str]] | None = None,   # (text, provenance)
    knowledge: list[tuple[str, str]] | None = None,
    constraints: list[str] | None = None,
    history: list[str] | None = None,
    token_limit: int = 8_000,
) -> LayeredContext:
    """Assemble a layered context under a token budget.

    Evidence is attempted first (highest priority after problem) and is
    truncated-with-marker rather than dropped; only knowledge/history
    chunks can be dropped entirely.
    """
    ctx = LayeredContext()
    budget = TokenBudget(limit=token_limit)

    def _add(layer: ContextLayer, text: str, prov: str = "",
             essential: bool = False) -> None:
        t = estimate_tokens(text)
        if not budget.try_spend(t, label=prov or layer.name):
            if essential:
                # shrink to fit instead of dropping
                shrunk, _ = _preserve(
                    text, max(200, budget.remaining * 4))
                t2 = estimate_tokens(shrunk)
                if budget.try_spend(t2, label=prov or layer.name):
                    ctx.chunks.append(ContextChunk(
                        layer=layer, text=shrunk, provenance=prov,
                        truncated=True, tokens=t2))
            return
        ctx.chunks.append(ContextChunk(
            layer=layer, text=text, provenance=prov, tokens=t))

    _add(ContextLayer.PROBLEM, problem, essential=True)
    for text, prov in evidence or []:
        shrunk, trunc = _preserve(text)
        _add(ContextLayer.EVIDENCE, shrunk, prov, essential=True)
        if trunc:
            ctx.chunks[-1].truncated = True
    for text, prov in knowledge or []:
        _add(ContextLayer.KNOWLEDGE, text, prov)
    for c in constraints or []:
        _add(ContextLayer.CONSTRAINTS, c, "constraints")
    for h in history or []:
        _add(ContextLayer.HISTORY, h, "history")

    ctx.budget_notes = budget.notes
    ctx.total_tokens = budget.spent
    ctx.digest = hashlib.sha256(ctx.render().encode()).hexdigest()[:16]
    return ctx
