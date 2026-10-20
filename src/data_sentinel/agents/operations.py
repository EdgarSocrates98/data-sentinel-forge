"""§9 — operational triggers feeding the Sentinel Coordinator.

Recebe alerta, regressão, comparação ou anomalia e produz uma
investigação delimitada. Regras duras:

- hipóteses são rotuladas observed/associated/probable/unknown —
  "confirmed cause" NUNCA é emitida por esta camada (§9.4);
- sem artefatos locais, a investigação declara a limitação em vez de
  fabricar achados;
- multi-hop sequencial entre especialistas: NÃO implementado neste
  ciclo — roteamento determinístico atual cobre os casos avaliados e
  loops entre agentes são proibidos (§9.6).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from data_sentinel.agents.guardrails import sanitize_untrusted
from data_sentinel.agents.investigator import investigate
from data_sentinel.core.contracts.agent import InvestigationReport
from data_sentinel.core.contracts.snapshot import ExecutionSnapshot
from data_sentinel.history.regression import detect_regressions


class TriggerKind(StrEnum):
    ALERT = "alert"
    REGRESSION = "regression"
    COMPARISON = "comparison"
    QUALITY_ANOMALY = "quality_anomaly"
    COST_ANOMALY = "cost_anomaly"


class CauseLabel(StrEnum):
    """§9.4 — rótulos permitidos. CONFIRMED é propositalmente ausente."""
    OBSERVED_REGRESSION = "observed_regression"
    ASSOCIATED_EVENT = "associated_event"
    PROBABLE_CAUSE = "probable_cause"
    UNKNOWN = "unknown"


@dataclass
class OperationalTrigger:
    kind: TriggerKind
    summary: str
    source_refs: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_problem(self) -> str:
        return sanitize_untrusted(
            f"[{self.kind}] {self.summary} "
            f"(refs: {', '.join(self.source_refs) or 'nenhuma'})",
            max_chars=2_000)


def trigger_investigation(
    trigger: OperationalTrigger,
    files: dict[str, str] | None = None,
) -> InvestigationReport:
    """Bounded operational investigation (§9.1/§9.2).

    Delegates to the standard `investigate()` pipeline — budgets and
    guardrails apply identically. Trigger context is recorded.
    """
    rep = investigate(trigger.to_problem(), files or {})
    rep.context["operational_trigger"] = {
        "kind": str(trigger.kind),
        "summary": trigger.summary[:500],
        "source_refs": list(trigger.source_refs)[:50],
    }
    if not files:
        rep.limitations.append(
            "trigger operacional sem artefatos locais — análise "
            "limitada a roteamento/contexto; nenhum achado fabricado")
    return rep


@dataclass
class Hypothesis:
    label: CauseLabel
    statement: str
    supporting: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"label": str(self.label), "statement": self.statement,
                "supporting": self.supporting,
                "limitations": self.limitations}


def evaluate_hypothesis(
    history: list[ExecutionSnapshot],
    current: ExecutionSnapshot,
) -> Hypothesis:
    """§9.3/§9.4 — compara histórico/métricas/config e rotula.

    Nunca retorna causa confirmada; correlação é declarada como tal.
    """
    findings = detect_regressions(history, current)
    if not findings:
        if current.failure is True:
            return Hypothesis(
                CauseLabel.OBSERVED_REGRESSION,
                "falha observada sem regressão de métricas",
                supporting=["current.failure=True"],
                limitations=["falha sem contexto de métricas — "
                             "causa não inferida"])
        return Hypothesis(
            CauseLabel.UNKNOWN,
            "sem regressão detectável — dados insuficientes",
            limitations=["histórico ou métricas ausentes"])

    supporting = [f"{f['metric']}: {f['rationale']}"
                  for f in findings]
    changes = _related_changes(history, current)
    if changes:
        return Hypothesis(
            CauseLabel.ASSOCIATED_EVENT,
            "regressão observada com alterações correlatas",
            supporting=supporting + changes,
            limitations=["correlação temporal não é causalidade — "
                         "investigar antes de remediar"])
    return Hypothesis(
        CauseLabel.OBSERVED_REGRESSION,
        "regressão observada sem alterações correlatas",
        supporting=supporting,
        limitations=["sem mudança declarada no período — "
                     "causa não inferida por esta camada"])


def _related_changes(history: list[ExecutionSnapshot],
                     current: ExecutionSnapshot) -> list[str]:
    out: list[str] = []
    if not history:
        return out
    prev = sorted(history, key=lambda s: s.started_at or "")[-1]
    if (prev.runtime and current.runtime
            and prev.runtime != current.runtime):
        out.append(f"runtime {prev.runtime} -> {current.runtime}")
    if (prev.config_fingerprint and current.config_fingerprint
            and prev.config_fingerprint
            != current.config_fingerprint):
        out.append("config fingerprint alterado")
    if (prev.input_bytes and current.input_bytes
            and prev.input_bytes > 0):
        ratio = current.input_bytes / prev.input_bytes
        if ratio > 1.5 or ratio < 0.66:
            out.append(f"volume de entrada {ratio:.1f}x")
    return out


def trigger_from_alert(alert: dict[str, Any]) -> OperationalTrigger:
    return OperationalTrigger(
        kind=TriggerKind.ALERT,
        summary=str(alert.get("message", "alerta")),
        source_refs=[str(alert.get("alert_id", ""))],
        payload={"watch_id": str(alert.get("watch_id", "")),
                 "kind": str(alert.get("kind", "")),
                 "severity": str(alert.get("severity", "")),
                 "findings": list(alert.get("findings", []))})


def trigger_from_regression(
    job_id: str, findings: list[dict[str, Any]],
) -> OperationalTrigger:
    metrics = ", ".join(str(f.get("metric", "?"))
                       for f in findings[:10]) or "?"
    return OperationalTrigger(
        kind=TriggerKind.REGRESSION,
        summary=f"regressão em {job_id}: {metrics}",
        source_refs=[job_id],
        payload={"job_id": job_id,
                 "findings": findings[:20]})


def new_trigger_id() -> str:
    return f"trig:{uuid.uuid4().hex[:12]}"
