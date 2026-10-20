"""Drift detection (ds-0043, §5.4-§5.6).

Compares a baseline ColumnProfile/sample against a current one.
Uses scipy.stats (ks_2samp / chi2_contingency) when the `stats` extra
is installed; falls back to documented heuristics otherwise. Every
result carries evidence + confidence — never asserts without a test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from data_sentinel.core.contracts import (
    DriftLevel,
    Finding,
    FindingCategory,
    FindingStatus,
    Severity,
)
from data_sentinel.quality.profile import ColumnProfile

try:
    from scipy import stats as sp_stats  # type: ignore[import-untyped]
    _HAS_SCIPY = True
except ImportError:  # pragma: no cover
    sp_stats = None
    _HAS_SCIPY = False

PSI_WARN = 0.1
PSI_ALERT = 0.25
MEAN_SHIFT_SIGMAS = 3.0


@dataclass
class DriftResult:
    column: str
    level: DriftLevel
    statistic: str          # psi | ks_pvalue | chi2_pvalue | mean_shift
    value: float | None
    threshold: float | None
    engine: str             # scipy | heuristic
    confidence: str         # CONFIRMED | PROBABLE | POSSIBLE | UNKNOWN
    evidence: str
    limitations: list[str] = field(default_factory=list)


def psi(expected: list[float], actual: list[float],
        bins: int = 10) -> float | None:
    """Population Stability Index between two distributions."""
    if not expected or not actual:
        return None
    lo = min(min(expected), min(actual))
    hi = max(max(expected), max(actual))
    if lo == hi:
        return 0.0

    def _hist(vals: list[float]) -> list[float]:
        h = [0] * bins
        for v in vals:
            idx = min(bins - 1,
                      max(0, int((v - lo) / (hi - lo) * bins)))
            h[idx] += 1
        total = sum(h) or 1
        return [max(c / total, 1e-6) for c in h]

    e, a = _hist(expected), _hist(actual)
    return sum((a[i] - e[i]) * math.log(a[i] / e[i])
               for i in range(bins))


def _psi_level(v: float | None) -> DriftLevel:
    if v is None:
        return DriftLevel.UNKNOWN
    if v >= PSI_ALERT:
        return DriftLevel.HIGH
    if v >= PSI_WARN:
        return DriftLevel.MEDIUM
    if v > 0.02:
        return DriftLevel.LOW
    return DriftLevel.NONE


def _p_level(p: float | None) -> DriftLevel:
    if p is None:
        return DriftLevel.UNKNOWN
    if p < 0.001:
        return DriftLevel.HIGH
    if p < 0.01:
        return DriftLevel.MEDIUM
    if p < 0.05:
        return DriftLevel.LOW
    return DriftLevel.NONE


def detect_drift(column: str,
                 baseline: list[float], current: list[float]) -> DriftResult:
    """Numeric drift: KS test (scipy) or PSI+mean-shift heuristic."""
    if len(baseline) < 5 or len(current) < 5:
        return DriftResult(column=column, level=DriftLevel.UNKNOWN,
                           statistic="insufficient", value=None,
                           threshold=None, engine="none",
                           confidence="UNKNOWN",
                           evidence="amostras insuficientes (<5)",
                           limitations=["não é possível inferir drift"])

    if _HAS_SCIPY:
        res = sp_stats.ks_2samp(baseline, current)
        p = float(res.pvalue)
        return DriftResult(
            column=column, level=_p_level(p),
            statistic="ks_pvalue", value=p, threshold=0.05,
            engine="scipy",
            confidence="CONFIRMED" if p < 0.01 else
            "PROBABLE" if p < 0.05 else "POSSIBLE",
            evidence=f"KS two-sample p={p:.4g} "
                     f"(n={len(baseline)} vs {len(current)})")

    psi_v = psi(baseline, current)
    level = _psi_level(psi_v)
    return DriftResult(
        column=column, level=level,
        statistic="psi", value=psi_v, threshold=PSI_WARN,
        engine="heuristic",
        confidence="PROBABLE" if level in (DriftLevel.MEDIUM,
                                           DriftLevel.HIGH)
        else "POSSIBLE",
        evidence=f"PSI={psi_v:.4g} (thresholds {PSI_WARN}/{PSI_ALERT})",
        limitations=["scipy ausente — PSI heurístico, sem teste de "
                     "significância formal"])


def detect_categorical_drift(column: str,
                             baseline: dict[str, int],
                             current: dict[str, int]) -> DriftResult:
    """Categorical drift via chi2 (scipy) or TV distance fallback."""
    keys = sorted(set(baseline) | set(current))
    b = [baseline.get(k, 0) for k in keys]
    c = [current.get(k, 0) for k in keys]
    if sum(b) < 5 or sum(c) < 5:
        return DriftResult(column=column, level=DriftLevel.UNKNOWN,
                           statistic="insufficient", value=None,
                           threshold=None, engine="none",
                           confidence="UNKNOWN",
                           evidence="contagens insuficientes")
    if _HAS_SCIPY:
        chi = sp_stats.chi2_contingency([b, c])
        p = float(chi.pvalue)
        return DriftResult(
            column=column, level=_p_level(p),
            statistic="chi2_pvalue", value=p, threshold=0.05,
            engine="scipy",
            confidence="CONFIRMED" if p < 0.01 else
            "PROBABLE" if p < 0.05 else "POSSIBLE",
            evidence=f"chi2 p={p:.4g} sobre {len(keys)} categorias")
    # total variation distance fallback
    tb, tc = sum(b), sum(c)
    tv = 0.5 * sum(abs(b[i] / tb - c[i] / tc) for i in range(len(keys)))
    level = (DriftLevel.HIGH if tv > 0.5 else DriftLevel.MEDIUM
             if tv > 0.25 else DriftLevel.LOW if tv > 0.1
             else DriftLevel.NONE)
    return DriftResult(
        column=column, level=level, statistic="tv_distance",
        value=tv, threshold=0.25, engine="heuristic",
        confidence="PROBABLE" if level != DriftLevel.NONE else "POSSIBLE",
        evidence=f"TV distance={tv:.4g}",
        limitations=["scipy ausente — sem teste formal de independência"])


def drift_from_profiles(baseline: ColumnProfile,
                        current: ColumnProfile) -> DriftResult:
    """Drift from two profiles (uses top_values for categoricals; for
    numerics only mean/std evidence — flagged as coarse)."""
    if baseline.dtype_inferred == "numeric":
        if baseline.mean is None or current.mean is None:
            return DriftResult(
                column=baseline.column, level=DriftLevel.UNKNOWN,
                statistic="insufficient", value=None, threshold=None,
                engine="none", confidence="UNKNOWN",
                evidence="perfis sem estatísticas numéricas")
        shift = abs(current.mean - baseline.mean)
        denom = baseline.stddev or 1e-9
        sigmas = shift / denom
        level = (DriftLevel.HIGH if sigmas > MEAN_SHIFT_SIGMAS
                 else DriftLevel.MEDIUM if sigmas > 2
                 else DriftLevel.LOW if sigmas > 1
                 else DriftLevel.NONE)
        return DriftResult(
            column=baseline.column, level=level,
            statistic="mean_shift", value=sigmas,
            threshold=MEAN_SHIFT_SIGMAS, engine="heuristic",
            confidence="POSSIBLE",
            evidence=f"deslocamento de média = {sigmas:.2f} sigmas",
            limitations=["agregado de perfis — drift distribucional "
                         "fino requer amostras brutas"])
    return detect_categorical_drift(baseline.column,
                                    baseline.top_values,
                                    current.top_values)


def drift_findings(results: list[DriftResult]) -> list[Finding]:
    out: list[Finding] = []
    for r in results:
        if r.level in (DriftLevel.NONE, DriftLevel.UNKNOWN):
            continue
        sev = (Severity.HIGH if r.level == DriftLevel.HIGH
               else Severity.MEDIUM)
        st = (FindingStatus.CONFIRMED if r.confidence == "CONFIRMED"
              else FindingStatus.PROBABLE)
        expl = (f"drift em '{r.column}' ({r.level.value}): {r.evidence}; "
                f"estatística={r.statistic}, engine={r.engine}. "
                + (" ".join(r.limitations) if r.limitations else ""))
        out.append(Finding(
            severity=sev, status=st,
            category=FindingCategory.DATA_QUALITY,
            explanation=expl,
            evidence_ids=[f"drift:{r.column}:{r.statistic}"],
            recommendations=["comparar janela temporal atual vs baseline",
                             "validar schema e upstream antes de "
                             "alterar consumidores"]))
    return out
