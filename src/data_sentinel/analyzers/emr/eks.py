"""EMR on EKS analyzer (ds-0063, §5).

Two offline inputs (§5.2-§5.3):
- emr-containers exports (virtual cluster + job runs);
- Kubernetes manifests/events exported via `kubectl get -o yaml|json`.

Priority: driver unschedulable, executor OOMKilled, pending executors,
insufficient nodes, image pull failure, eviction/node pressure,
restart loops, IAM/service-account gaps. Direct K8s access is opt-in,
authenticated, read-only — never default.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import yaml

from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.core.contracts.entities import (
    CapabilityManifest,
    DiagnosticRequest,
    Evidence,
    Finding,
)
from data_sentinel.core.contracts.enums import (
    EvidenceProvenance,
    FindingCategory,
    FindingStatus,
    Platform,
    Severity,
    SourceType,
)
from data_sentinel.core.security import InputFile
from data_sentinel.core.security.sanitize import sanitize_evidence_excerpt

_UNSCHED = ("insufficient cpu", "insufficient memory",
            "0/ nodes are available", "didn't match node selector",
            "untolerated taint", "pod unschedulable")
_IMAGE = ("imagepullbackoff", "errimagepull", "image pull")
_OOM = ("oomkilled", "exit code 137")
_EVICT = ("evicted", "node pressure", "memorypressure",
          "diskpressure")


def _docs(text: str) -> list[dict[str, Any]]:
    """kubetl -o yaml/json → list of objects (multi-doc YAML ok)."""
    out: list[dict[str, Any]] = []
    try:
        for d in yaml.safe_load_all(text):
            if isinstance(d, dict):
                out.append(d)
    except yaml.YAMLError:
        pass
    if not out:
        try:
            raw = json.loads(text)
            if isinstance(raw, dict):
                items = raw.get("items")
                out = (items if isinstance(items, list)
                       else [raw])
        except json.JSONDecodeError:
            pass
    return [o for o in out if isinstance(o, dict)]


class EmrEksAnalyzer(Analyzer):
    @property
    def analyzer_id(self) -> str:
        return "emr.eks"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def supported_platforms(self) -> tuple[str, ...]:
        return (Platform.SPARK,)

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (SourceType.OTHER,)

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
            "Manifests/eventos exportados (kubectl -o) — não há acesso "
            "direto ao cluster por padrão (§5.3)",
            "emr-containers DescribeJobRun só quando exportado; sem ele "
            "a correlação vc↔pod fica limitada",
            "Capacidade de nós só avaliada via eventos de scheduling "
            "exportados — sem Cluster Autoscaler real",
            "IRSA/service-account revisado estaticamente — nunca "
            "sugerimos permissões administrativas",
        )

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=list(self.supported_platforms),
            supported_runtimes=["emr-6.x-eks", "emr-7.x-eks"],
            required_permissions=["filesystem:read"],
            supported_operations=["analyze_emr_eks"],
            limitations=list(self.limitations),
        )

    def analyze(self, request: DiagnosticRequest,
                inputs: Sequence[InputFile]) -> AnalysisResult:
        started = time.monotonic()
        captured = datetime.now(UTC)
        self.validate_input(request, inputs)
        findings: list[Finding] = []
        evidence: list[Evidence] = []
        limitations = list(self.limitations)

        for inp in inputs:
            digest = hashlib.sha256(inp.text.encode()).hexdigest()
            objs = _docs(inp.text)
            if not objs:
                limitations.append(
                    f"{inp.path}: nenhum objeto K8s/JSON reconhecido")
                continue

            def _ev(s: str, conf: float = 0.8,
                    _p: str = str(inp.path),
                    _d: str = digest) -> Evidence:
                e = Evidence(source="emr_eks",
                             source_location=_p,
                             captured_at=captured,
                             content_hash=_d,
                             sanitized_excerpt=
                                 sanitize_evidence_excerpt(
                                     s, max_chars=500),
                             provenance=EvidenceProvenance.DECLARED,
                             confidence=conf)
                evidence.append(e)
                return e

            for obj in objs:
                kind = obj.get("kind", "")
                if kind == "Pod":
                    self._pod(obj, _ev, findings)
                elif kind == "Event":
                    self._event(obj, _ev, findings)
                elif "virtualCluster" in json.dumps(obj) or \
                        obj.get("jobRun"):
                    self._jobrun(obj, _ev, findings)
                else:
                    limitations.append(
                        f"{inp.path}: kind '{kind or '?'}' não "
                        "interpretado — preservado")

        if not findings:
            findings.append(Finding(
                category=FindingCategory.UNKNOWN,
                severity=Severity.INFO,
                status=FindingStatus.UNKNOWN,
                explanation="Sem achados EMR on EKS — não prova saúde: "
                            "events/pods/jobs podem não ter sido "
                            "exportados",
                alternatives=["exportar kubectl get pods,events -A "
                              "-o yaml"]))
        return AnalysisResult(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.version,
            request_id=request.request_id,
            findings=findings, evidence=evidence,
            limitations=limitations,
            duration_ms=int((time.monotonic() - started) * 1000))

    def _pod(self, pod: dict[str, Any], _ev: Any,
             findings: list[Finding]) -> None:
        meta = pod.get("metadata", {})
        name = meta.get("name", "?")
        ns = meta.get("namespace", "default")
        status = pod.get("status", {})
        phase = status.get("phase", "")
        role = ("driver" if "driver" in name else
                "executor" if "executor" in name else "pod")

        for cs in (status.get("containerStatuses") or []):
            st = cs.get("state", {}) or {}
            last = cs.get("lastState", {}) or {}
            waiting = st.get("waiting", {}) or {}
            term = (st.get("terminated") or
                    last.get("terminated") or {})
            blob = json.dumps(
                {**waiting, **term}, default=str).lower()

            if any(w in blob for w in _OOM):
                ev = _ev(f"{role} {name} OOMKilled "
                         f"rc={cs.get('restartCount', 0)}", 0.9)
                findings.append(Finding(
                    category=FindingCategory.OUT_OF_MEMORY,
                    severity=Severity.HIGH,
                    status=FindingStatus.CONFIRMED,
                    explanation=f"{role.capitalize()} pod {name} "
                                f"(ns={ns}) OOMKilled — "
                                f"restarts={cs.get('restartCount', 0)}",
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "aumentar memory request/limit do executor",
                        "revisar spark.executor.memoryOverhead"]))
            elif any(w in blob for w in _IMAGE):
                ev = _ev(f"{role} {name} image pull falhou", 0.9)
                findings.append(Finding(
                    category=FindingCategory.DEPENDENCY,
                    severity=Severity.HIGH,
                    status=FindingStatus.CONFIRMED,
                    explanation=f"{role.capitalize()} pod {name} com "
                                "falha de pull de imagem",
                    evidence_ids=[ev.evidence_id],
                    validation_steps=["verificar registry, tag, "
                                      "pull secrets"]))
            elif any(w in blob for w in _EVICT):
                ev = _ev(f"{role} {name} evicted/pressure", 0.8)
                findings.append(Finding(
                    category=FindingCategory.DISK_SPACE,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.CONFIRMED,
                    explanation=f"{role.capitalize()} pod {name} "
                                "evictido por pressão de nó",
                    evidence_ids=[ev.evidence_id]))
            elif int(cs.get("restartCount", 0) or 0) >= 3:
                ev = _ev(f"{role} {name} restarts="
                         f"{cs.get('restartCount')}", 0.7)
                findings.append(Finding(
                    category=FindingCategory.DEPENDENCY,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.PROBABLE,
                    explanation=f"{role.capitalize()} pod {name} em "
                                f"restart loop "
                                f"({cs.get('restartCount')}x)",
                    evidence_ids=[ev.evidence_id],
                    validation_steps=["inspecionar logs do container "
                                      "anterior"]))

        if phase == "Pending":
            conds = status.get("conditions") or []
            blob = json.dumps(conds, default=str).lower()
            if any(w in blob for w in _UNSCHED):
                ev = _ev(f"{role} {name} Pending: unschedulable", 0.8)
                findings.append(Finding(
                    category=FindingCategory.CONFIGURATION,
                    severity=Severity.HIGH,
                    status=FindingStatus.CONFIRMED,
                    explanation=f"{role.capitalize()} pod {name} "
                                "unschedulable (recursos/taints/"
                                "selectors) — §5.4",
                    evidence_ids=[ev.evidence_id],
                    validation_steps=[
                        "kubectl describe pod para motivo exato",
                        "revisar requests vs capacidade dos nós"]))

    def _event(self, ev_obj: dict[str, Any], _ev: Any,
               findings: list[Finding]) -> None:
        reason = ev_obj.get("reason", "")
        msg = ev_obj.get("message", "")
        involved = (ev_obj.get("involvedObject") or {}).get("name", "?")
        blob = f"{reason} {msg}".lower()
        if any(w in blob for w in _UNSCHED):
            e = _ev(f"Event {reason}: {msg[:120]}", 0.8)
            findings.append(Finding(
                category=FindingCategory.CONFIGURATION,
                severity=Severity.MEDIUM,
                status=FindingStatus.CONFIRMED,
                explanation=f"Scheduling failure em {involved}: "
                            f"{reason} — {msg[:120]}",
                evidence_ids=[e.evidence_id],
                recommendations=["revisar node groups/taints/"
                                 "requests"]))
        elif any(w in blob for w in _EVICT):
            e = _ev(f"Event {reason}: {msg[:120]}", 0.7)
            findings.append(Finding(
                category=FindingCategory.DISK_SPACE,
                severity=Severity.MEDIUM,
                status=FindingStatus.PROBABLE,
                explanation=f"Pressão de nó afetando {involved}: "
                            f"{reason}",
                evidence_ids=[e.evidence_id]))

    def _jobrun(self, obj: dict[str, Any], _ev: Any,
                findings: list[Finding]) -> None:
        jr = obj.get("jobRun", obj)
        jid = jr.get("id") or jr.get("jobRunId", "?")
        state = jr.get("state", "")
        details = jr.get("stateDetails", "")
        if state in ("FAILED", "SUBMISSION_FAILED"):
            e = _ev(f"jobRun {jid} {state}: {details[:140]}", 0.9)
            findings.append(Finding(
                category=FindingCategory.DEPENDENCY,
                severity=Severity.HIGH,
                status=FindingStatus.CONFIRMED,
                explanation=f"Job run {jid} {state}: "
                            f"{details[:140] or 'sem detalhes'} — "
                            "falha antes de Spark init se driver "
                            "não agendou (§5.6)",
                evidence_ids=[e.evidence_id],
                validation_steps=["kubectl get pods -n <ns> para "
                                  "driver/executors"]))
        vc = obj.get("virtualCluster") or {}
        if isinstance(vc, dict) and not (vc.get("id")):
            pass  # nothing to assert without data
