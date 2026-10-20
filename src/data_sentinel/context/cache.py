"""Bounded context cache (§6.3).

LRU-bounded, content-addressed. Evictions are counted; no unbounded
growth. Never caches secrets — callers pass already-redacted text.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass, field


@dataclass
class ContextCache:
    max_entries: int = 256
    max_bytes: int = 8_000_000
    evictions: int = 0
    _store: OrderedDict[str, str] = field(
        default_factory=OrderedDict)
    _bytes: int = 0

    @staticmethod
    def key(text: str, *, namespace: str = "") -> str:
        return f"{namespace}:{hashlib.sha256(text.encode()).hexdigest()[:24]}"

    def get(self, key: str) -> str | None:
        v = self._store.get(key)
        if v is not None:
            self._store.move_to_end(key)
        return v

    def put(self, key: str, value: str) -> None:
        size = len(value.encode())
        if size > self.max_bytes:
            return  # never cache oversized
        while (len(self._store) >= self.max_entries
               or self._bytes + size > self.max_bytes):
            _, evicted = self._store.popitem(last=False)
            self._bytes -= len(evicted.encode())
            self.evictions += 1
        old = self._store.get(key)
        if old is not None:
            self._bytes -= len(old.encode())
        self._store[key] = value
        self._bytes += size

    def __len__(self) -> int:
        return len(self._store)
