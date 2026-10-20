"""Token economy (§6.4).

Rough deterministic estimator (~4 chars/token) + a budget that tracks
spend per component and never silently drops evidence — overflow goes
to ``dropped`` accounting with an explicit note.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def estimate_tokens(text: str) -> int:
    """Deterministic estimate — no tokenizer dependency."""
    return max(1, (len(text) + 3) // 4) if text else 0


@dataclass
class TokenBudget:
    limit: int
    spent: int = 0
    dropped_chunks: int = 0
    dropped_tokens: int = 0
    notes: list[str] = field(default_factory=list)

    def try_spend(self, tokens: int, *, label: str = "") -> bool:
        if self.spent + tokens <= self.limit:
            self.spent += tokens
            return True
        self.dropped_chunks += 1
        self.dropped_tokens += tokens
        self.notes.append(
            f"chunk '{label}' excluído por budget "
            f"({tokens} tok; restante {self.limit - self.spent})")
        return False

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.spent)
