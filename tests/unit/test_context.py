"""Context engineering tests (ds-0054)."""

from data_sentinel.context import (
    ContextCache,
    ContextLayer,
    TokenBudget,
    build_context,
    estimate_tokens,
)


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd" * 4) == 4


def test_budget_drops_and_notes() -> None:
    b = TokenBudget(limit=10)
    assert b.try_spend(6, label="a")
    assert not b.try_spend(6, label="b")
    assert b.dropped_chunks == 1 and b.notes


def test_context_order_and_digest() -> None:
    ctx = build_context(
        problem="job falhou",
        evidence=[("erro X na linha 3", "log:glue")],
        knowledge=[("doc relevante", "kb:1")],
        constraints=["budget 8k"],
        history=["run anterior ok"])
    r = ctx.render()
    assert r.index("[PROBLEM]") < r.index("[EVIDENCE]")
    assert r.index("[EVIDENCE]") < r.index("[KNOWLEDGE]")
    assert ctx.digest and ctx.total_tokens > 0


def test_evidence_truncated_never_silent() -> None:
    big = "x" * 10_000
    ctx = build_context(problem="p", evidence=[(big, "ev1")])
    ev = next(c for c in ctx.chunks if c.layer == ContextLayer.EVIDENCE)
    assert ev.truncated
    assert "TRUNCATED" in ev.text
    assert "truncado" in ctx.render()


def test_budget_overflow_drops_knowledge_not_evidence() -> None:
    ctx = build_context(
        problem="p",
        evidence=[("evidência importante", "ev")],
        knowledge=[("doc enorme " + "y" * 30000, "kb")],
        token_limit=500)
    layers = {c.layer for c in ctx.chunks}
    assert ContextLayer.EVIDENCE in layers
    assert ctx.budget_notes  # drop registrado


def test_cache_lru_and_bounds() -> None:
    c = ContextCache(max_entries=3, max_bytes=1_000)
    c.put("a", "1")
    c.put("b", "2")
    c.put("c", "3")
    assert len(c) == 3
    c.get("a")  # a becomes MRU
    c.put("d", "4")
    assert c.evictions >= 1
    assert c.get("b") is None  # LRU evicted
    c.put("huge", "x" * 2_000)
    assert c.get("huge") is None  # oversized never cached


def test_cache_key_stable() -> None:
    k1 = ContextCache.key("texto", namespace="n")
    k2 = ContextCache.key("texto", namespace="n")
    assert k1 == k2 and k1.startswith("n:")
