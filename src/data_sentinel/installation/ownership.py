"""File ownership tracking (§2.4) — facade over the vendored
installkit ``Ledger`` (``forge/InstallLedger/v1``).

The kit ledger is the single source of truth for which files Sentinel
owns: only ``managed`` entries may be overwritten or removed; foreign
files are skipped/adopted, never clobbered.
"""

from __future__ import annotations

from pathlib import Path

from data_sentinel import _installkit as kit
from data_sentinel.core.exceptions import SentinelError
from data_sentinel.installation.contracts import ManagedFile
from data_sentinel.installation.service import STATE_DIR


def ledger_path(root: Path) -> Path:
    return root / STATE_DIR / kit.LEDGER_NAME


class OwnershipLedger:
    """Typed view over a kit ledger rooted at ``root``."""

    def __init__(self, root: Path):
        # The kit's _load_json swallows parse errors into an empty ledger;
        # surface corruption honestly instead of silently losing ownership.
        import json

        path = ledger_path(root)
        if path.is_file():
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise SentinelError(
                    code="LEDGER_CORRUPT",
                    message=f"installation ledger unreadable: {path}",
                    details={"path": str(path)},
                ) from exc
            if not isinstance(doc, dict) or doc.get("schema") != "forge/InstallLedger/v1":
                raise SentinelError(
                    code="LEDGER_CORRUPT",
                    message=f"installation ledger has unexpected schema: {path}",
                    details={"path": str(path)},
                )
        self._kit = kit.Ledger.load(root / STATE_DIR)

    @property
    def managed(self) -> list[ManagedFile]:
        return [
            ManagedFile(
                path=rel,
                sha256=e.get("sha256", ""),
                component=e.get("kind", "state"),
                host="",
            )
            for rel, e in sorted(self._kit.entries().items())
            if e.get("managed")
        ]

    def is_managed(self, path: Path, root: Path | None = None) -> bool:
        rel = _rel(path, root)
        entry = self._kit.get(rel)
        return bool(entry and entry.get("managed"))

    def is_intact(self, path: Path, root: Path) -> bool:
        rel = _rel(path, root)
        entry = self._kit.get(rel)
        if not entry:
            return False
        target = root / rel
        return target.is_file() and kit._sha_file(target) == entry.get("sha256")

    def record(self, rel: str, data: bytes, kind: str, action: str) -> None:
        self._kit.record(rel, data, kind, action)
        self._kit.save()

    def remove(self, rel: str) -> None:
        self._kit.drop(rel)
        self._kit.save()


def _rel(path: Path, root: Path | None) -> str:
    if root is not None:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()
    return path.as_posix()


def load_ledger(root: Path) -> OwnershipLedger:
    try:
        return OwnershipLedger(root)
    except SentinelError:
        raise
    except Exception as exc:
        raise SentinelError(
            code="LEDGER_CORRUPT",
            message=f"installation ledger unreadable: {ledger_path(root)}",
            details={"path": str(ledger_path(root))},
        ) from exc
