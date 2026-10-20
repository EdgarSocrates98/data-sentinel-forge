"""Tool registry + executor (ds-0052).

Each tool maps to real analyzer functionality — file-based inputs reuse
``run_diagnostics``; in-process helpers reuse the quality/lineage
modules directly. Permissions declared per tool; cloud-write and
destructive are never registered.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    Platform,
    SourceType,
)
from data_sentinel.core.contracts.agent import (
    BLOCKED_PERMISSIONS,
    ToolDescriptor,
    ToolInvocation,
    ToolPermission,
    ToolResult,
)

MAX_OUTPUT_CHARS = 200_000


class ToolUnavailableError(RuntimeError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDescriptor] = {}

    def register(self, desc: ToolDescriptor) -> None:
        if set(desc.permissions) & BLOCKED_PERMISSIONS:
            raise ToolUnavailableError(
                f"permissão bloqueada neste ciclo: {desc.permissions}")
        self._tools[desc.tool_id] = desc

    def get(self, tool_id: str) -> ToolDescriptor:
        t = self._tools.get(tool_id)
        if t is None:
            raise ToolUnavailableError(f"tool desconhecida: {tool_id}")
        return t

    def list_tools(self) -> list[ToolDescriptor]:
        return sorted(self._tools.values(), key=lambda t: t.tool_id)

    def to_mcp_manifest(self) -> list[dict[str, Any]]:
        return [{
            "name": t.tool_id,
            "description": t.description,
            "inputSchema": t.input_schema or {
                "type": "object", "properties": {
                    "file": {"type": "string"}},
                "required": ["file"]},
        } for t in self.list_tools()]


def _file_tool(tool_id: str, source: SourceType, desc: str,
               *, network: bool = False,
               perms: list[ToolPermission] | None = None,
               extra: dict[str, Any] | None = None) -> ToolDescriptor:
    return ToolDescriptor(
        tool_id=tool_id, name=tool_id.split(".")[-1],
        description=desc,
        input_schema={"type": "object",
                      "properties": {"file": {"type": "string"}},
                      "required": ["file"]},
        permissions=perms or [ToolPermission.LOCAL_READ],
        network_required=network,
        estimated_cost="low",
        output_limitations=["saída truncada em "
                            f"{MAX_OUTPUT_CHARS} chars"],
        side_effects=[] if not (extra or {}).get("write") else
        ["grava artefato de relatório"],
    )


def build_default_registry() -> ToolRegistry:
    """Register only tools backed by real, working analyzers."""
    r = ToolRegistry()
    r.register(_file_tool(
        "sentinel.glue.inspect_run", SourceType.GLUE_JOB,
        "Inspeciona metadados/export de um run Glue (offline)."))
    r.register(_file_tool(
        "sentinel.glue.diagnose_run", SourceType.GLUE_JOB,
        "Diagnostica um run Glue a partir de metadata exportada."))
    r.register(_file_tool(
        "sentinel.cloudwatch.analyze_logs", SourceType.CLOUDWATCH_LOG,
        "Correlaciona exceções e padrões em logs CloudWatch/exportados."))
    r.register(_file_tool(
        "sentinel.spark.analyze_plan", SourceType.SPARK_PLAN,
        "Analisa plano físico Spark: shuffles, scans, broadcast."))
    r.register(_file_tool(
        "sentinel.spark.optimize", SourceType.SPARK_PLAN,
        "Recomendações de otimização a partir de plano/stats."))
    r.register(_file_tool(
        "sentinel.sql.analyze", SourceType.SQL_QUERY,
        "Análise AST de consulta SQL: antipadrões, joins, hints."))
    r.register(_file_tool(
        "sentinel.iceberg.inspect_metadata", SourceType.ICEBERG_METADATA,
        "Inspeciona metadados Iceberg (v1/v2/v3, snapshots, manifests)."))
    r.register(_file_tool(
        "sentinel.iceberg.analyze_operation",
        SourceType.ICEBERG_METADATA,
        "Analisa operações MERGE/APPEND e riscos de commit."))
    r.register(_file_tool(
        "sentinel.lakeformation.assess_access",
        SourceType.ACCESS_CONTEXT,
        "Avalia contexto de acesso LF/FGAC/cross-account."))
    r.register(_file_tool(
        "sentinel.lakehouse.compatibility", SourceType.ACCESS_CONTEXT,
        "Compatibilidade runtime x tabela (FGAC/FTA, formatos, ops)."))
    r.register(_file_tool(
        "sentinel.iam.analyze_policy", SourceType.POLICY_DOC,
        "Avaliador offline de policies IAM/S3/KMS."))
    r.register(ToolDescriptor(
        tool_id="sentinel.quality.assess", name="assess",
        description="Normaliza resultados exportados de qualidade.",
        input_schema={"type": "object", "properties": {
            "file": {"type": "string"},
            "adapter": {"type": "string"}},
                      "required": ["file"]},
        permissions=[ToolPermission.LOCAL_READ]))
    r.register(ToolDescriptor(
        tool_id="sentinel.quality.detect_drift", name="detect_drift",
        description="Drift entre amostras baseline/atual.",
        input_schema={"type": "object", "properties": {
            "baseline_file": {"type": "string"},
            "current_file": {"type": "string"}},
                      "required": ["baseline_file", "current_file"]},
        permissions=[ToolPermission.LOCAL_READ]))
    r.register(ToolDescriptor(
        tool_id="sentinel.lineage.ingest", name="ingest",
        description="Ingere eventos OpenLineage e monta grafo.",
        input_schema={"type": "object", "properties": {
            "file": {"type": "string"}}, "required": ["file"]},
        permissions=[ToolPermission.LOCAL_READ]))
    r.register(ToolDescriptor(
        tool_id="sentinel.lineage.impact", name="impact",
        description="Impacto potencial (alcançabilidade no grafo).",
        input_schema={"type": "object", "properties": {
            "file": {"type": "string"},
            "target": {"type": "string"}},
                      "required": ["file", "target"]},
        permissions=[ToolPermission.LOCAL_READ]))
    r.register(_file_tool(
        "sentinel.emr.analyze_ec2", SourceType.OTHER,
        "Diagnostica EMR on EC2 (cluster/steps/capacidade exportados)."))
    r.register(_file_tool(
        "sentinel.emr.analyze_serverless", SourceType.OTHER,
        "Diagnostica EMR Serverless (apps/job runs exportados)."))
    r.register(_file_tool(
        "sentinel.emr.analyze_eks", SourceType.OTHER,
        "Diagnostica EMR on EKS (manifests/eventos K8s exportados)."))
    r.register(ToolDescriptor(
        tool_id="sentinel.emr.estimate_cost", name="estimate_cost",
        description="Estima custo EMR declarado (tabela estática, "
                    "nunca billing).",
        input_schema={"type": "object", "properties": {
            "platform": {"type": "string"},
            "vcpu_hours": {"type": "number"},
            "mem_gb_hours": {"type": "number"},
            "instance_type": {"type": "string"},
            "count": {"type": "number"},
            "hours": {"type": "number"}},
                      "required": ["platform"]},
        permissions=[ToolPermission.LOCAL_READ]))
    r.register(ToolDescriptor(
        tool_id="sentinel.doctor.import_bundle", name="import_bundle",
        description="Importa bundle Forge Doctor (offline).",
        input_schema={"type": "object", "properties": {
            "file": {"type": "string"}}, "required": ["file"]},
        permissions=[ToolPermission.LOCAL_READ]))
    return r


def _roots_for(file: str,
               allowed_roots: list[Path] | None) -> list[Path]:
    """Explicit roots when a caller restricts scope (MCP). Without them
    the fallback is the file's own dir + cwd — effectively unrestricted
    for a readable path (a file is always inside its parent); that is
    the intended CLI behavior, not a sandbox (ds-0106, review)."""
    if allowed_roots is not None:
        return allowed_roots
    return [Path(file).resolve().parent, Path.cwd()]


def _checked(file: str, allowed_roots: list[Path] | None) -> Path:
    """Resolve *file* enforcing explicit roots when provided."""
    from data_sentinel.core.security.paths import safe_resolve
    if allowed_roots is None:
        return Path(file).resolve()
    return safe_resolve(file, allowed_roots=allowed_roots)


def _run_diagnostics(tool: ToolDescriptor, source: SourceType,
                     file: str,
                     allowed_roots: list[Path] | None = None
                     ) -> dict[str, Any]:
    from data_sentinel.core.security.paths import read_input_file
    from data_sentinel.diagnostics.orchestrator import AnalysisLimits, run_diagnostics

    limits = AnalysisLimits()
    inputs = [read_input_file(
        file, max_file_bytes=50 * 1024 * 1024,
        allowed_roots=_roots_for(file, allowed_roots))]
    req = DiagnosticRequest(
        source_type=source,
        artifact_references=[ArtifactReference(uri=file)],
        platform=Platform.AWS_GLUE)
    outcome = run_diagnostics(req, inputs, limits=limits)
    rep = outcome.report
    return {
        "report_id": rep.report_id,
        "findings": [f.model_dump(mode="json") for f in rep.findings],
        "evidence": [e.model_dump(mode="json") for e in outcome.evidence],
        "summary": rep.summary,
        "limitations": rep.limitations,
    }


_SOURCE_FOR: dict[str, SourceType] = {
    "sentinel.glue.inspect_run": SourceType.GLUE_JOB,
    "sentinel.glue.diagnose_run": SourceType.GLUE_JOB,
    "sentinel.cloudwatch.analyze_logs": SourceType.CLOUDWATCH_LOG,
    "sentinel.spark.analyze_plan": SourceType.SPARK_PLAN,
    "sentinel.spark.optimize": SourceType.SPARK_PLAN,
    "sentinel.sql.analyze": SourceType.SQL_QUERY,
    "sentinel.iceberg.inspect_metadata": SourceType.ICEBERG_METADATA,
    "sentinel.iceberg.analyze_operation": SourceType.ICEBERG_METADATA,
    "sentinel.lakeformation.assess_access": SourceType.ACCESS_CONTEXT,
    "sentinel.lakehouse.compatibility": SourceType.ACCESS_CONTEXT,
    "sentinel.iam.analyze_policy": SourceType.POLICY_DOC,
}


def execute_tool(inv: ToolInvocation, registry: ToolRegistry | None = None,
                 *, allowed_roots: list[Path] | None = None,
                 dry_run: bool = False) -> ToolResult:
    """Execute a registered tool invocation with budget accounting."""
    reg = registry or build_default_registry()
    t0 = time.perf_counter()
    try:
        desc = reg.get(inv.tool_id)
    except ToolUnavailableError as exc:
        return ToolResult(invocation_id=inv.invocation_id, ok=False,
                          error=str(exc),
                          duration_ms=(time.perf_counter() - t0) * 1000)
    if dry_run:
        return ToolResult(
            invocation_id=inv.invocation_id, tool_id=inv.tool_id,
            ok=True, output={"dry_run": True,
                             "permissions": [p.value
                                             for p in desc.permissions]})
    try:
        out = _dispatch(inv, desc, allowed_roots)
        text = json.dumps(out, ensure_ascii=False, default=str)
        truncated = len(text) > MAX_OUTPUT_CHARS
        return ToolResult(
            invocation_id=inv.invocation_id, tool_id=inv.tool_id,
            ok=True, output=out,
            duration_ms=(time.perf_counter() - t0) * 1000,
            truncated=truncated,
            limitations=out.get("limitations") or [])
    except Exception as exc:  # tool errors are data, not crashes
        return ToolResult(invocation_id=inv.invocation_id,
                          tool_id=inv.tool_id, ok=False,
                          error=f"{type(exc).__name__}: {exc}",
                          duration_ms=(time.perf_counter() - t0) * 1000)


_EMR_ANALYZER: dict[str, str] = {
    "sentinel.emr.analyze_ec2": "emr.ec2",
    "sentinel.emr.analyze_serverless": "emr.serverless",
    "sentinel.emr.analyze_eks": "emr.eks",
}


def _run_one_analyzer(analyzer_id: str, file: str,
                      allowed_roots: list[Path] | None = None
                      ) -> dict[str, Any]:
    from data_sentinel.analyzers import registry as analyzers
    from data_sentinel.core.security.paths import read_input_file

    analyzer = analyzers.get(analyzer_id)
    inputs = [read_input_file(
        file, max_file_bytes=50 * 1024 * 1024,
        allowed_roots=_roots_for(file, allowed_roots))]
    req = DiagnosticRequest(
        source_type=SourceType.OTHER,
        artifact_references=[ArtifactReference(uri=file)],
        platform=Platform.SPARK)
    res = analyzer.analyze(req, inputs)
    return {
        "analyzer": analyzer_id,
        "findings": [f.model_dump(mode="json") for f in res.findings],
        "limitations": res.limitations,
    }


def _dispatch(inv: ToolInvocation, desc: ToolDescriptor,
              allowed_roots: list[Path] | None = None) -> dict[str, Any]:
    tid = inv.tool_id
    inp = inv.input
    if tid == "sentinel.emr.estimate_cost":
        from data_sentinel.analyzers.emr.cost import estimate_ec2, estimate_eks, estimate_serverless
        platform = str(inp.get("platform", ""))
        fn = {"emr_serverless": lambda: estimate_serverless(
                inp.get("vcpu_hours"), inp.get("mem_gb_hours"),
                inp.get("storage_gb_hours")),
              "emr_ec2": lambda: estimate_ec2(
                inp.get("instance_type"), inp.get("count"),
                inp.get("hours")),
              "emr_eks": lambda: estimate_eks(
                inp.get("vcpu_hours"), inp.get("mem_gb_hours"),
                inp.get("cluster_hours"))}.get(platform)
        if fn is None:
            return {"error": f"plataforma desconhecida: {platform!r}"}
        return fn().to_dict()
    if tid in _EMR_ANALYZER:
        return _run_one_analyzer(_EMR_ANALYZER[tid],
                                 str(inp["file"]), allowed_roots)
    if tid in _SOURCE_FOR:
        return _run_diagnostics(desc, _SOURCE_FOR[tid],
                                str(inp["file"]), allowed_roots)
    if tid == "sentinel.quality.assess":
        from data_sentinel.quality import normalize
        file = str(inp["file"])
        obs = normalize(_checked(file, allowed_roots)
                        .read_text(encoding="utf-8"),
                        adapter=str(inp.get("adapter") or "auto"),
                        provenance=file)
        return {"observations": [o.model_dump(mode="json")
                                 for o in obs], "count": len(obs)}
    if tid == "sentinel.quality.detect_drift":
        import json as _j

        from data_sentinel.quality.drift import detect_drift
        base = _j.loads(_checked(str(inp["baseline_file"]),
                                 allowed_roots)
                        .read_text(encoding="utf-8"))
        cur = _j.loads(_checked(str(inp["current_file"]),
                                allowed_roots)
                       .read_text(encoding="utf-8"))
        dres = detect_drift("metric", [float(v) for v in base],
                            [float(v) for v in cur])
        return {"drift": dres.__dict__}
    if tid == "sentinel.lineage.ingest":
        from data_sentinel.lineage import parse_openlineage_events
        from data_sentinel.lineage.graph import build_graph
        file = str(inp["file"])
        ing = parse_openlineage_events(
            _checked(file, allowed_roots).read_text(encoding="utf-8"),
            provenance=file)
        g = build_graph(ing.events)
        return {"events": len(ing.events), "kind": ing.kind.value,
                "downstream": {k: sorted(v)
                               for k, v in g.downstream.items()},
                "limitations": ing.limitations + g.limitations}
    if tid == "sentinel.lineage.impact":
        from data_sentinel.core.contracts import DatasetReference
        from data_sentinel.lineage import parse_openlineage_events
        from data_sentinel.lineage.graph import build_graph, impact
        file = str(inp["file"])
        g = build_graph(parse_openlineage_events(
            _checked(file, allowed_roots).read_text(encoding="utf-8"),
            provenance=file).events)
        ns, _, name = str(inp["target"]).rpartition("/")
        imp = impact(g, DatasetReference(namespace=ns,
                                         name=name or inp["target"]))
        return imp.model_dump(mode="json")
    if tid == "sentinel.doctor.import_bundle":
        from data_sentinel.adapters.doctor import import_doctor_bundle
        res = import_doctor_bundle(
            _checked(str(inp["file"]), allowed_roots))
        return {"format": res.format,
                "findings": [f.model_dump(mode="json")
                             for f in res.findings],
                "warnings": res.warnings}
    raise ToolUnavailableError(f"sem implementação: {tid}")
