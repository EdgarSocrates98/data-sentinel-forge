"""Investigation memory (§7.4) — file-backed, append-only JSONL.

Persists InvestigationState snapshots + retrieval events keyed by
investigation id. No unbounded growth: files are per-investigation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from data_sentinel.core.contracts.agent import InvestigationState


@dataclass
class InvestigationMemory:
    root: Path
    _states: dict[str, InvestigationState] = field(default_factory=dict)

    def _file(self, iid: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_"
                       for c in iid)[:80]
        return self.root / f"{safe}.jsonl"

    def save(self, state: InvestigationState) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        f = self._file(state.investigation_id)
        with f.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(state.model_dump(mode="json"),
                                default=str) + "\n")
        self._states[state.investigation_id] = state
        return f

    def load(self, iid: str) -> InvestigationState | None:
        if iid in self._states:
            return self._states[iid]
        f = self._file(iid)
        if not f.exists():
            return None
        last = f.read_text(encoding="utf-8").strip().splitlines()[-1]
        st = InvestigationState.model_validate_json(last)
        self._states[iid] = st
        return st

    def history(self, iid: str) -> list[dict[str, object]]:
        f = self._file(iid)
        if not f.exists():
            return []
        return [json.loads(line) for line in
                f.read_text(encoding="utf-8").splitlines() if line.strip()]
