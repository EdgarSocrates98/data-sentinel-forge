"""Evidence-aware lexical retrieval (§7.1-§7.3).

TF-IDF-ish scoring: rare terms weigh more; every returned chunk keeps
source + provenance. Deterministic, stdlib-only.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from data_sentinel.core.contracts.agent import KnowledgeChunk, RetrievalResult

_TOKEN = re.compile(r"[a-z0-9_]+", re.I)
_STOP = {"a", "o", "e", "de", "do", "da", "em", "um", "uma", "the",
         "of", "to", "in", "and", "or", "is", "para", "com", "por"}


def _terms(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)
            if t.lower() not in _STOP and len(t) > 2]


class KnowledgeBase:
    """In-memory chunk store with deterministic lexical search."""

    def __init__(self) -> None:
        self._chunks: dict[str, KnowledgeChunk] = {}
        self._df: dict[str, int] = {}

    def add(self, chunk: KnowledgeChunk) -> None:
        if chunk.chunk_id in self._chunks:
            return
        self._chunks[chunk.chunk_id] = chunk
        for t in set(_terms(chunk.text)):
            self._df[t] = self._df.get(t, 0) + 1

    def add_text(self, text: str, *, source: str, kind: str = "doc",
                 provenance: str = "") -> None:
        self.add(KnowledgeChunk(
            chunk_id=f"{source}:{len(self._chunks)}",
            source=source, text=text, kind=kind,
            provenance=provenance or source))

    def load_dir(self, path: Path, *, glob: str = "*.md",
                 kind: str = "doc") -> int:
        n = 0
        for f in sorted(path.rglob(glob)):
            if f.is_file() and f.stat().st_size < 500_000:
                self.add_text(f.read_text(encoding="utf-8",
                                          errors="replace"),
                              source=str(f), kind=kind)
                n += 1
        return n

    def search(self, query: str, *, top_k: int = 5
               ) -> RetrievalResult:
        q = _terms(query)
        if not q:
            return RetrievalResult(query=query, limitations=[
                "query vazia após normalização"])
        n_docs = max(1, len(self._chunks))
        scored: list[tuple[float, KnowledgeChunk]] = []
        for c in self._chunks.values():
            tf: dict[str, int] = {}
            for t in _terms(c.text):
                tf[t] = tf.get(t, 0) + 1
            score = 0.0
            for t in q:
                if t in tf:
                    idf = math.log(1 + n_docs / (1 + self._df.get(t, 0)))
                    score += tf[t] * idf
            if score > 0:
                scored.append((score, c))
        scored.sort(key=lambda kv: (-kv[0], kv[1].chunk_id))
        out = []
        for score, c in scored[:top_k]:
            out.append(c.model_copy(update={
                "metadata": {**c.metadata, "score": f"{score:.3f}"}}))
        return RetrievalResult(
            query=query, chunks=out, method="lexical-tfidf",
            limitations=[] if out else [
                "nenhum chunk relevante — resposta não deve inventar"])


def retrieve(kb: KnowledgeBase, query: str, *, top_k: int = 5
             ) -> RetrievalResult:
    return kb.search(query, top_k=top_k)
