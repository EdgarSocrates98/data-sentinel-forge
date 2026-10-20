"""§7 — remediation plans: DRAFT→…→APPROVED; execução local only.

Regras duras:
- aprovação NUNCA provoca execução cloud automática (§7.3);
- dry-run devolve dados estruturados, nunca executa scripts/SQL (§7.4);
- rollback declarado quando viável — nenhuma reversão universal
  prometida (§7.5);
- executor local restrito a LOCAL_ACTION_ALLOWLIST.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from data_sentinel.core.contracts.entities import ContractModel, Finding
from data_sentinel.core.contracts.enums import FindingCategory


class PlanState(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class RemediationType(StrEnum):
    SPARK_CONFIG_TUNING = "spark_config_tuning"
    JOIN_OPTIMIZATION = "join_optimization"
    ICEBERG_MAINTENANCE = "iceberg_maintenance"
    DQ_CORRECTION = "dq_correction"
    CAPACITY_ADJUSTMENT = "capacity_adjustment"
    IAM_LF_INVESTIGATION = "iam_lf_investigation"
    RETRY_BEHAVIOR = "retry_behavior"
    ALERT_THRESHOLD = "alert_threshold"


_ALLOWED: dict[PlanState, frozenset[PlanState]] = {
    PlanState.DRAFT: frozenset({PlanState.VALIDATED,
                               PlanState.REJECTED}),
    PlanState.VALIDATED: frozenset({PlanState.AWAITING_APPROVAL,
                                   PlanState.DRAFT,
                                   PlanState.REJECTED}),
    PlanState.AWAITING_APPROVAL: frozenset({PlanState.APPROVED,
                                           PlanState.REJECTED,
                                           PlanState.EXPIRED}),
    PlanState.APPROVED: frozenset({PlanState.EXPIRED}),
    PlanState.REJECTED: frozenset({PlanState.DRAFT}),
    PlanState.EXPIRED: frozenset({PlanState.DRAFT}),
}

# §7 — ações que o executor local pode aplicar neste ciclo.
# Nenhuma toca AWS/cloud; tudo é estado local do Sentinel.
LOCAL_ACTION_ALLOWLIST: frozenset[str] = frozenset({
    "update_watch_threshold",      # ajustar thresholds de watch local
    "suppress_alert",              # suprimir alerta por janela
    "escalate_notification",       # elevar severidade de notificação
})


class ProposedChange(ContractModel):
    target: str = Field(min_length=1)
    change: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    local_action: str | None = None   # só executável se no allowlist


class RemediationPlan(ContractModel):
    plan_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str = Field(min_length=1)
    remediation_type: RemediationType
    finding_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    proposed_changes: list[ProposedChange] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    expected_effects: list[str] = Field(default_factory=list)
    validation_procedure: list[str] = Field(default_factory=list)
    rollback_proposal: str | None = None
    rollback_limitations: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    approval_required: bool = True
    state: PlanState = PlanState.DRAFT
    state_history: list[dict[str, str]] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    approved_by: str | None = None


def _transition(plan: RemediationPlan, to: PlanState,
                note: str = "") -> RemediationPlan:
    if to not in _ALLOWED[plan.state]:
        raise ValueError(
            f"transição inválida {plan.state}→{to}; permitidas: "
            f"{sorted(_ALLOWED[plan.state])}")
    plan.state_history.append({"from": str(plan.state),
                               "to": str(to), "note": note,
                               "at": datetime.now(UTC).isoformat()})
    plan.state = to
    return plan


def validate_plan(plan: RemediationPlan) -> list[str]:
    """DRAFT→VALIDATED checklist; retorna problemas (vazio=ok)."""
    problems: list[str] = []
    if not plan.proposed_changes:
        problems.append("sem proposed_changes")
    if not plan.finding_ids and not plan.evidence_ids:
        problems.append("sem referências a findings/evidência")
    if not plan.validation_procedure:
        problems.append("sem validation_procedure")
    if not plan.rollback_proposal:
        problems.append("sem rollback_proposal declarado")
    return problems


def submit_for_approval(plan: RemediationPlan) -> RemediationPlan:
    problems = validate_plan(plan)
    if problems:
        raise ValueError(f"plano incompleto: {problems}")
    if plan.state == PlanState.DRAFT:
        _transition(plan, PlanState.VALIDATED)
    return _transition(plan, PlanState.AWAITING_APPROVAL)


def approve(plan: RemediationPlan, approver: str) -> RemediationPlan:
    if not approver:
        raise ValueError("approver obrigatório — aprovação nunca "
                         "anônima")
    plan.approved_by = approver
    return _transition(plan, PlanState.APPROVED,
                       note=f"aprovado por {approver}")


def reject(plan: RemediationPlan, reason: str) -> RemediationPlan:
    return _transition(plan, PlanState.REJECTED, note=reason)


def dry_run(plan: RemediationPlan) -> dict[str, Any]:
    """§7.4 — prévia estruturada; nunca executa nada."""
    return {
        "plan_id": plan.plan_id,
        "state": str(plan.state),
        "would_change": [
            {"target": c.target, "change": c.change,
             "params": c.params,
             "executable_locally": bool(
                 c.local_action and c.local_action
                 in LOCAL_ACTION_ALLOWLIST),
             "requires": "cloud/manual execution"
             if not c.local_action
             else c.local_action}
            for c in plan.proposed_changes],
        "preconditions": list(plan.preconditions),
        "risks": list(plan.risks),
        "rollback": plan.rollback_proposal,
        "note": "dry-run: nenhuma alteração aplicada",
    }


def execute_local(plan: RemediationPlan,
                  apply_fn: dict[str, Any] | None = None
                  ) -> dict[str, Any]:
    """Executor local — só ações no allowlist, plano APPROVED.

    `apply_fn` maps local_action -> callable(params)->result.
    Ações cloud/destrutivas não existem aqui por design.
    """
    if plan.state != PlanState.APPROVED:
        raise ValueError(f"execução requer APPROVED; estado "
                         f"atual {plan.state}")
    results: list[dict[str, Any]] = []
    applied = apply_fn or {}
    for c in plan.proposed_changes:
        if c.local_action is None:
            results.append({"target": c.target, "status": "SKIPPED",
                            "reason": "execução manual/cloud — fora do "
                                      "executor local"})
            continue
        if c.local_action not in LOCAL_ACTION_ALLOWLIST:
            results.append({"target": c.target, "status": "BLOCKED",
                            "reason": f"ação '{c.local_action}' fora "
                                      "do allowlist"})
            continue
        fn = applied.get(c.local_action)
        if fn is None:
            results.append({"target": c.target,
                            "action": c.local_action,
                            "status": "PENDING",
                            "reason": "sem apply_fn registrada — "
                                      "registrado para aplicação"})
            continue
        results.append({"target": c.target,
                        "action": c.local_action,
                        "status": "APPLIED",
                        "result": fn(c.params)})
    return {"plan_id": plan.plan_id, "results": results,
            "note": "nenhuma chamada cloud foi feita"}


def export_plan(plan: RemediationPlan) -> dict[str, Any]:
    """§7.6 — bundle interoperável para consumo futuro do Spark Forge."""
    return {
        "contract": "forge-contracts/1",
        "kind": "sentinel.remediation_plan",
        "plan_id": plan.plan_id,
        "title": plan.title,
        "remediation_type": str(plan.remediation_type),
        "state": str(plan.state),
        "finding_ids": plan.finding_ids,
        "evidence_ids": plan.evidence_ids,
        "proposed_changes": [
            {"target": c.target, "change": c.change,
             "params": c.params}
            for c in plan.proposed_changes],
        "validation_procedure": plan.validation_procedure,
        "rollback_proposal": plan.rollback_proposal,
        "limitations": ["plano supervisionado — implementação é "
                        "responsabilidade do consumidor; aprovação "
                        "não transfere autoridade de execução"],
    }


_CATEGORY_MAP: dict[FindingCategory, RemediationType] = {
    FindingCategory.OUT_OF_MEMORY: RemediationType.SPARK_CONFIG_TUNING,
    FindingCategory.DISK_SPACE: RemediationType.CAPACITY_ADJUSTMENT,
    FindingCategory.DATA_SKEW: RemediationType.JOIN_OPTIMIZATION,
    FindingCategory.CONFIGURATION: RemediationType.SPARK_CONFIG_TUNING,
    FindingCategory.PERMISSIONS: RemediationType.IAM_LF_INVESTIGATION,
    FindingCategory.NETWORK_IO: RemediationType.RETRY_BEHAVIOR,
    FindingCategory.TIMEOUT: RemediationType.RETRY_BEHAVIOR,
    FindingCategory.EXECUTOR_LOSS: RemediationType.CAPACITY_ADJUSTMENT,
    FindingCategory.SQL_ANTIPATTERN: RemediationType.JOIN_OPTIMIZATION,
    FindingCategory.DATA_QUALITY: RemediationType.DQ_CORRECTION,
    FindingCategory.COST: RemediationType.CAPACITY_ADJUSTMENT,
    FindingCategory.SECURITY: RemediationType.IAM_LF_INVESTIGATION,
}


def plan_for_finding(finding: Finding, *,
                     title: str | None = None) -> RemediationPlan:
    """Gera plano DRAFT a partir de um Finding — supervisionado."""
    rtype = _CATEGORY_MAP.get(finding.category,
                              RemediationType.SPARK_CONFIG_TUNING)
    plan = RemediationPlan(
        title=title or f"Remediar: {finding.explanation[:80]}",
        remediation_type=rtype,
        finding_ids=[finding.finding_id],
        evidence_ids=list(finding.evidence_ids),
        proposed_changes=[
            ProposedChange(target=finding.category.value,
                           change=r,
                           params={})
            for r in finding.recommendations] or
        [ProposedChange(target="manual",
                        change="investigação manual necessária")],
        preconditions=["validar baseline antes de aplicar",
                       "confirmar janela de mudança"],
        risks=["mudança de configuração pode degradar desempenho "
               "se premissas não se confirmarem"],
        expected_effects=list(finding.recommendations),
        validation_procedure=list(finding.validation_steps) or
        ["reexecutar workload e comparar métricas com baseline"],
        rollback_proposal="reverter configuração para valores "
                          "anteriores registrados",
        rollback_limitations=["reversão de efeitos de dados não é "
                              "garantida — apenas de configuração"],
        required_permissions=["sentinel.local.apply"],
        expires_at=None)
    plan.state_history.append({
        "from": "", "to": "DRAFT",
        "note": "plano gerado a partir de finding",
        "at": plan.created_at.isoformat()})
    return plan
