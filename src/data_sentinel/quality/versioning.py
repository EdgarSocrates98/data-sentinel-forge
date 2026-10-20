"""Contract version compatibility (§3.4).

Semver-ish comparison: MAJOR differences break; MINOR/PATCH differences
are forward-compatible reads with a warning.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VersionCheck:
    compatible: bool
    reason: str
    warnings: list[str] = field(default_factory=list)


def _parse(v: str) -> tuple[int, int, int]:
    parts = (v or "0").split(".")
    nums = []
    for p in parts[:3]:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return nums[0], nums[1], nums[2]


def check_version_compat(expected: str, found: str) -> VersionCheck:
    """expected = contract version the consumer was built for."""
    em, en, ep = _parse(expected)
    fm, fn, fp = _parse(found)
    if em != fm:
        return VersionCheck(
            compatible=False,
            reason=f"MAJOR diverge: esperado {expected}, encontrado {found}")
    warnings: list[str] = []
    if (fn, fp) > (en, ep):
        warnings.append(
            f"contrato {found} é mais novo que o esperado {expected} — "
            "campos desconhecidos serão preservados mas não avaliados")
    return VersionCheck(compatible=True,
                        reason="compatível", warnings=warnings)
