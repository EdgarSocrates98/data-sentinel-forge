"""Investigation orchestrator (ds-0058, §10).

Deterministic end-to-end: route problem → execute specialist tools →
collect findings → independent validation → RCA → InvestigationReport.
No LLM required anywhere in the path.
"""

from __future__ import annotations

from data_sentinel.agents.guardrails import (
    GuardrailError,
    PermissionClass,
    check_tool_permission,
    sanitize_untrusted,
)
from data_sentinel.agents.specialists import get_specialist, route
from data_sentinel.core.contracts.agent import InvestigationReport, ToolInvocation
from data_sentinel.core.contracts.entities import Evidence, Finding
from data_sentinel.reasoning import EvidenceValidator, RootCauseEngine
from data_sentinel.tools.registry import execute_tool


def _tool_for_file(agent_id: str, file_kind: str) -> str | None:
    """Pick the first allowed tool of the specialist for the kind."""
    spec = get_specialist(agent_id)
    return spec.allowed_tools[0] if spec.allowed_tools else None


def investigate(problem: str, files: dict[str, str]
                ) -> InvestigationReport:
    """files: {tool_id: path} — explicit, no silent tool guessing."""
    problem = sanitize_untrusted(problem, max_chars=4_000)
    rep = InvestigationReport(
        report_id="inv:local", investigation_id="inv:local",
        problem=problem)
    rep.agents_used = route(problem)

    findings: list[Finding] = []
    evidence: list[Evidence] = []
    seen_evidence: set[str] = set()
    for tool_id, path in sorted(files.items()):
        try:
            check_tool_permission(tool_id, PermissionClass.READ_LOCAL)
        except GuardrailError as exc:
            rep.limitations.append(str(exc))
            continue
        inv = ToolInvocation(
            invocation_id=f"inv-{len(rep.tools_used)}",
            tool_id=tool_id, input={"file": path})
        res = execute_tool(inv)
        rep.context.setdefault("tool_calls", []).append({
            "tool_id": tool_id, "ok": res.ok,
            "duration_ms": res.duration_ms})
        rep.tools_used.append(tool_id)
        if not res.ok:
            rep.limitations.append(f"{tool_id}: {res.error}")
            continue
        out = res.output if isinstance(res.output, dict) else {}
        for f in out.get("findings", []):
            try:
                findings.append(Finding.model_validate(f))
            except Exception:
                rep.limitations.append(
                    f"{tool_id}: finding malformado ignorado")
        for ev in out.get("evidence", []):
            try:
                parsed = Evidence.model_validate(ev)
                if parsed.evidence_id not in seen_evidence:
                    seen_evidence.add(parsed.evidence_id)
                    evidence.append(parsed)
            except Exception:
                rep.limitations.append(
                    f"{tool_id}: evidence malformada ignorada")
        for lim in out.get("limitations", []):
            rep.limitations.append(f"{tool_id}: {lim}")

    rep.findings = findings
    rep.evidence = sorted(evidence, key=lambda e: e.evidence_id)

    # independent validation (§8.3)
    vrep = EvidenceValidator().validate(findings)
    rep.context["validation"] = {
        "checked": vrep.checked,
        "errors": [i.issue for i in vrep.errors],
        "warnings": [i.issue for i in vrep.issues
                     if i.severity == "warning"],
    }
    if not vrep.ok:
        rep.limitations.append(
            "validador independente encontrou erros — veja context")

    # root cause (§8.1)
    rca = RootCauseEngine().analyze(findings)
    rep.hypotheses_supported = [
        h for h in rca.hypotheses if h.status == "supported"]
    rep.context["rca_scores"] = rca.scores
    if rca.primary:
        rep.conclusions.append(
            f"causa-raiz provável: {rca.primary.statement} "
            f"(confiança {rca.primary.confidence})")
    rep.limitations.extend(rca.limitations)
    return rep
