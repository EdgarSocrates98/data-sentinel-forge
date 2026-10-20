"""EMR on EC2 analyzer (ds-0061, §3.2-§3.6).

Priority diagnoses: provisioning/bootstrap/step failure, container OOM,
executor lost, YARN shortage, disk pressure, spot interruption,
shuffle/network, misconfigured resources, idle waste. Every conclusion
cites evidence; absent layers become limitations, not guesses.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from data_sentinel.analyzers.emr.parser import EmrClusterDoc, parse_cluster
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

_SPOT_TYPES = {"SPOT"}
_FAIL_WORDS = ("outofmemory", "out of memory", "oomkilled",
               "container killed", "exit code 137")
_LOST_WORDS = ("executor lost", "lost executor", "slave lost",
               "nodelost", "node lost")
_SHUFFLE_WORDS = ("fetchfailed", "fetch failed", "shuffle",
                  "connection refused", "network")
_DISK_WORDS = ("no space left", "disk full", "yarn local dirs",
               "java.io.ioexception: no space")


class EmrEc2Analyzer(Analyzer):
    @property
    def analyzer_id(self) -> str:
        return "emr.ec2"

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
            "DescribeCluster/ListSteps exportados — não é acesso direto "
            "às APIs (§3.4)",
            "Métricas YARN/EC2 só quando fornecidas; sem elas, "
            "diagnósticos de utilização ficam UNKNOWN",
            "Spot interruption inferida de InstanceGroups + falha, "
            "nunca afirmada sem CloudTrail/eventos",
            "Sem métricas de disco: disk pressure só via texto de erro",
        )

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=list(self.supported_platforms),
            supported_runtimes=["emr-6.x", "emr-7.x"],
            required_permissions=["filesystem:read"],
            supported_operations=["analyze_emr_ec2"],
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
            doc = parse_cluster(inp.text, source=str(inp.path))
            limitations.extend(
                f"{inp.path}: {w}" for w in doc.warnings)
            if doc.extras:
                limitations.append(
                    f"{inp.path}: campos não reconhecidos preservados "
                    f"sem interpretação: {sorted(doc.extras)}")

            def _ev(snippet: str, conf: float = 0.8, _d: str = digest,
                    _p: str = str(inp.path)) -> Evidence:
                e = Evidence(
                    source="emr_ec2",
                    source_location=_p,
                    captured_at=captured,
                    content_hash=_d,
                    sanitized_excerpt=sanitize_evidence_excerpt(
                        snippet, max_chars=500),
                    provenance=EvidenceProvenance.DECLARED,
                    confidence=conf)
                evidence.append(e)
                return e

            self._cluster(doc, _ev, findings)
            self._steps(doc, _ev, findings)
            self._capacity(doc, _ev, findings, limitations)

        if not findings:
            findings.append(Finding(
                category=FindingCategory.UNKNOWN,
                severity=Severity.INFO,
                status=FindingStatus.UNKNOWN,
                explanation="Documento EMR sem achados — não prova "
                            "saúde: métricas não fornecidas",
                alternatives=["fornecer métricas YARN/CloudWatch",
                              "fornecer logs de step/driver"]))
        return AnalysisResult(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.version,
            request_id=request.request_id,
            findings=findings,
            evidence=evidence,
            limitations=limitations,
            duration_ms=int((time.monotonic() - started) * 1000))

    # ---- §3.2 cluster state / termination ----
    def _cluster(self, doc: EmrClusterDoc, _ev: Any, findings: list[Finding]
                 ) -> None:
        c = doc.cluster
        if not c:
            return
        status = c.get("Status", {})
        state = status.get("State", "")
        change = status.get("StateChangeReason", {}) or {}
        timeline = c.get("Status", {}).get("Timeline", {})
        cid = c.get("Id", "?")

        if state in ("TERMINATED_WITH_ERRORS", "TERMINATING"):
            msg = change.get("Message", "")
            code = change.get("Code", "")
            cat = FindingCategory.CONFIGURATION
            if "bootstrap" in msg.lower() or "BOOTSTRAP" in code:
                cat = FindingCategory.DEPENDENCY
            ev = _ev(f"cluster {cid}: state={state} "
                     f"code={code} msg={msg[:120]}", 0.9)
            findings.append(Finding(
                category=cat,
                severity=Severity.HIGH,
                status=FindingStatus.CONFIRMED,
                explanation=f"Cluster {cid} terminou com erro "
                            f"({code or 'sem código'}): {msg[:160]}",
                evidence_ids=[ev.evidence_id],
                validation_steps=["verificar logs de bootstrap em "
                                  "s3://…/node/"],
            ))
        elif state == "TERMINATED" and timeline:
            ready = timeline.get("ReadyDateTime")
            end = timeline.get("EndDateTime")
            if ready and end:
                hours = (end - ready) / 3600 if isinstance(
                    ready, (int, float)) else 0
                if hours > 4 and not doc.steps:
                    ev = _ev(
                        f"cluster {cid} viveu {hours:.1f}h sem steps "
                        "exportados", 0.6)
                    findings.append(Finding(
                        category=FindingCategory.COST,
                        severity=Severity.MEDIUM,
                        status=FindingStatus.POSSIBLE,
                        explanation=f"Cluster {cid} rodou ~{hours:.1f}h; "
                                    "nenhum step exportado — possível "
                                    "idle-time waste (§3.6)",
                        evidence_ids=[ev.evidence_id],
                        alternatives=["steps podem não ter sido "
                                      "exportados"]))

    # ---- §3.3 step diagnostics ----
    def _steps(self, doc: EmrClusterDoc, _ev: Any, findings: list[Finding]
               ) -> None:
        for st in doc.steps:
            sid = st.get("Id", "?")
            name = st.get("Name", "")
            status = st.get("Status", {})
            state = status.get("State", "")
            fd = (status.get("FailureDetails") or {})
            reason = fd.get("Reason", "")
            log = fd.get("LogFile", "")
            blob = " ".join([reason, log, str(fd.get("Message", ""))]).lower()

            if state != "FAILED":
                continue
            cat, sev = FindingCategory.UNKNOWN, Severity.HIGH
            if any(w in blob for w in _FAIL_WORDS):
                cat = FindingCategory.OUT_OF_MEMORY
            elif any(w in blob for w in _LOST_WORDS):
                cat = FindingCategory.EXECUTOR_LOSS
            elif any(w in blob for w in _DISK_WORDS):
                cat = FindingCategory.DISK_SPACE
            elif any(w in blob for w in _SHUFFLE_WORDS):
                cat = FindingCategory.NETWORK_IO
            ev = _ev(f"step {sid} '{name}' FAILED: {reason[:160]}", 0.9)
            findings.append(Finding(
                category=cat, severity=sev,
                status=(FindingStatus.CONFIRMED
                        if cat != FindingCategory.UNKNOWN
                        else FindingStatus.PROBABLE),
                explanation=f"Step {sid} ('{name}') falhou: "
                            f"{reason[:160] or 'sem reason'}",
                evidence_ids=[ev.evidence_id],
                validation_steps=[
                    "inspecionar driver/executor logs do step",
                    "correlacionar com Spark application id se "
                    "disponível"],
                alternatives=[] if cat != FindingCategory.UNKNOWN
                else ["razão de falha não classificada — revisar "
                      "logs manualmente"]))

    # ---- §3.5 capacity / spot ----
    def _capacity(self, doc: EmrClusterDoc, _ev: Any,
                  findings: list[Finding], limitations: list[str]
                  ) -> None:
        groups = doc.instance_groups + doc.instance_fleets
        if not groups:
            limitations.append(
                "InstanceGroups/Fleets não exportados — análise de "
                "capacidade/spot indisponível")
            return
        spot = [g for g in groups
                if g.get("Market", "").upper() in _SPOT_TYPES
                or (g.get("InstanceFleetType") and
                g.get("LaunchSpecifications", {}).get(
                    "SpotSpecification"))]
        c = doc.cluster
        state = c.get("Status", {}).get("State", "")
        if spot and state in ("TERMINATED_WITH_ERRORS", "TERMINATING"):
            types = sorted({g.get("InstanceGroupType", "?")
                            for g in spot})
            ev = _ev(f"grupos spot {types} + cluster {state}", 0.6)
            findings.append(Finding(
                category=FindingCategory.DEPENDENCY,
                severity=Severity.MEDIUM,
                status=FindingStatus.POSSIBLE,
                explanation="Cluster terminou com erro e usa instâncias "
                            f"Spot em {types} — interrupção Spot é "
                            "hipótese, não confirmada (§3.5)",
                evidence_ids=[ev.evidence_id],
                alternatives=["falha por configuração, bootstrap ou "
                              "aplicação"],
                validation_steps=["verificar Spot interruption notices "
                                  "no CloudTrail/EventBridge"]))
