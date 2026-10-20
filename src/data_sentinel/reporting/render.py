"""Presentation layer: DiagnosticReport → terminal / Markdown / JSON.

Separation of concerns: analyzers produce contracts; renderers only
present. No diagnostic logic lives here.
"""

from collections.abc import Sequence

from data_sentinel.core.contracts import DiagnosticReport, Evidence

_STATUS_ORDER = ("CONFIRMED", "PROBABLE", "POSSIBLE", "UNKNOWN")


def render_json(report: DiagnosticReport) -> str:
    return report.to_json()


def render_terminal(
    report: DiagnosticReport,
    evidence: Sequence[Evidence],
    *,
    mode_label: str | None = None,
) -> str:
    ev_by_id = {e.evidence_id: e for e in evidence}
    lines: list[str] = []
    if mode_label:
        lines.append(f"modo: {mode_label}")
    lines.append(f"relatório {report.report_id} (schema {report.schema_version})")
    lines.append(f"resumo: {report.summary}")
    if report.analyzer_versions:
        lines.append(
            "analyzers: "
            + ", ".join(f"{k}@{v}" for k, v in sorted(report.analyzer_versions.items()))
        )
    for finding in sorted(
        report.findings,
        key=lambda f: (_STATUS_ORDER.index(f.status.value), f.severity.value),
    ):
        lines.append(
            f"\n[{finding.severity.value}/{finding.status.value}] "
            f"{finding.category.value}"
        )
        lines.append(f"  {finding.explanation}")
        for ev_id in finding.evidence_ids:
            ev = ev_by_id.get(ev_id)
            if ev:
                lines.append(f"  evidência: {ev.source_location}")
                lines.append(f"    {ev.sanitized_excerpt[:200]}")
        for rec_text in finding.recommendations:
            lines.append(f"  recomendação: {rec_text}")
        for step in finding.validation_steps:
            lines.append(f"  validação: {step}")
    if report.recommendations:
        lines.append("\nrecomendações estruturadas:")
        for rec in report.recommendations:
            lines.append(
                f"  [{rec.recommendation_id}] {rec.target}: "
                f"{rec.proposed_change}"
            )
    if report.limitations:
        lines.append("\nlimitações:")
        for lim in report.limitations:
            lines.append(f"  - {lim}")
    return "\n".join(lines)


def render_markdown(
    report: DiagnosticReport,
    evidence: Sequence[Evidence],
    *,
    mode_label: str | None = None,
) -> str:
    ev_by_id = {e.evidence_id: e for e in evidence}
    md: list[str] = ["# Data Sentinel — Relatório de Diagnóstico", ""]

    md += ["## Sumário executivo", ""]
    md.append(f"- **Relatório:** `{report.report_id}` (schema `{report.schema_version}`)")
    md.append(f"- **Criado em:** {report.created_at.isoformat()}")
    md.append(f"- **Resumo:** {report.summary}")
    if mode_label:
        md.append(f"- **Modo:** {mode_label}")
    if report.environment:
        md.append(f"- **Ambiente:** {report.environment.name}")
    md.append("")

    md += ["## Contexto do job/artefatos", ""]
    for ref in report.references:
        md.append(f"- `{ref}`")
    md.append("")

    md += ["## Achados", ""]
    if not report.findings:
        md.append("_Nenhum achado._")
    ordered = sorted(
        report.findings,
        key=lambda f: (_STATUS_ORDER.index(f.status.value), f.severity.value),
    )
    for i, finding in enumerate(ordered, start=1):
        md.append(
            f"### {i}. {finding.category.value} — "
            f"{finding.severity.value} / {finding.status.value}"
        )
        md.append("")
        md.append(finding.explanation)
        md.append("")
        if finding.evidence_ids:
            md.append("**Evidências:**")
            for ev_id in finding.evidence_ids:
                ev = ev_by_id.get(ev_id)
                if ev:
                    md.append(f"- `{ev.source_location}` — `{ev.sanitized_excerpt[:200]}`")
            md.append("")
        if finding.recommendations:
            md.append("**Recomendações:**")
            for rec_text in finding.recommendations:
                md.append(f"- {rec_text}")
            md.append("")
        if finding.validation_steps:
            md.append("**Validação:**")
            for step in finding.validation_steps:
                md.append(f"- {step}")
            md.append("")

    if report.recommendations:
        md += ["## Recomendações estruturadas", ""]
        for rec in report.recommendations:
            md.append(f"### `{rec.recommendation_id}` — {rec.target}")
            md.append("")
            md.append(f"- **Mudança proposta:** {rec.proposed_change}")
            md.append(f"- **Justificativa:** {rec.rationale}")
            if rec.expected_effect:
                md.append(f"- **Benefício esperado (hipótese):** {rec.expected_effect}")
            if rec.estimated_risk:
                md.append(f"- **Riscos:** {rec.estimated_risk}")
            if rec.validation_plan:
                md.append(f"- **Validação:** {rec.validation_plan}")
            if rec.rollback_plan:
                md.append(f"- **Rollback:** {rec.rollback_plan}")
            md.append("")

    md += ["## Limitações", ""]
    if report.limitations:
        for lim in report.limitations:
            md.append(f"- {lim}")
    else:
        md.append("_Nenhuma declarada._")
    md.append("")

    md += ["## Versões dos analyzers", ""]
    for name, version in sorted(report.analyzer_versions.items()):
        md.append(f"- `{name}` v{version}")
    md.append("")
    return "\n".join(md)
