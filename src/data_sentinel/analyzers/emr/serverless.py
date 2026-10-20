"""EMR Serverless analyzer (ds-0062, §4).

Offline diagnostics over exported ListApplications/GetApplication/
ListJobRuns/GetJobRun JSON. Priority: app unavailable, submission,
resource exhaustion, slow startup, driver/executor failures, capacity,
retries, missing logs. Cost is always "estimated", never billing (§4.5).
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

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

_SLOW_START_SECONDS = 300      # >5min pending before running
_RETRY_FLAG = 1                # >1 attempt


def _jobs(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return [j for j in (raw.get("jobRuns")
                        or raw.get("JobRuns") or [])
            if isinstance(j, dict)]


class EmrServerlessAnalyzer(Analyzer):
    @property
    def analyzer_id(self) -> str:
        return "emr.serverless"

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
            "GetApplication/GetJobRun exportados — sem acesso à API "
            "emr-serverless",
            "Utilização de recursos só quando totalResourceUtilization "
            "fornecido — advisor vira hipótese sem elas",
            "Custos são ESTIMADOS a partir de uso declarado x tabela "
            "estática — nunca billing real (§4.5)",
            "Logs ausentes viram limitação, não presunção de falha",
        )

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=list(self.supported_platforms),
            supported_runtimes=["emr-serverless-6.x", "emr-serverless-7.x"],
            required_permissions=["filesystem:read"],
            supported_operations=["analyze_emr_serverless"],
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
            try:
                raw = json.loads(inp.text)
            except json.JSONDecodeError as exc:
                limitations.append(f"{inp.path}: JSON inválido ({exc})")
                continue
            calls = raw.get("calls", raw) if isinstance(raw, dict) else {}
            app = calls.get("application") or calls.get(
                "Application") or {}
            jobs = _jobs(calls)
            if isinstance(calls.get("jobRun"), dict):
                jobs.append(calls["jobRun"])
            elif isinstance(calls.get("JobRun"), dict):
                jobs.append(calls["JobRun"])

            def _ev(s: str, conf: float = 0.8, _d: str = digest,
                    _p: str = str(inp.path)) -> Evidence:
                e = Evidence(source="emr_serverless",
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

            self._application(app, _ev, findings)
            for j in jobs:
                self._job_run(j, _ev, findings, limitations)

        if not findings:
            findings.append(Finding(
                category=FindingCategory.UNKNOWN,
                severity=Severity.INFO,
                status=FindingStatus.UNKNOWN,
                explanation="Sem achados EMR Serverless — não prova "
                            "saúde: utilização/logs não fornecidos",
                alternatives=["exportar GetJobRun com "
                              "totalResourceUtilization"]))
        return AnalysisResult(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.version,
            request_id=request.request_id,
            findings=findings, evidence=evidence,
            limitations=limitations,
            duration_ms=int((time.monotonic() - started) * 1000))

    def _application(self, app: dict[str, Any], _ev: Any,
                     findings: list[Finding]) -> None:
        if not app:
            return
        state = app.get("state") or app.get("State", "")
        name = app.get("name") or app.get("applicationId", "?")
        if state in ("TERMINATED", "STOPPED"):
            auto = (app.get("autoStopConfiguration") or {})
            ev = _ev(f"app {name} state={state} autoStop={auto}", 0.8)
            findings.append(Finding(
                category=FindingCategory.CONFIGURATION,
                severity=Severity.LOW,
                status=FindingStatus.PROBABLE,
                explanation=f"Aplicação {name} está {state} — jobs não "
                            "serão aceitos até STARTED (§4.2)",
                evidence_ids=[ev.evidence_id],
                validation_steps=["verificar autoStartConfiguration "
                                  "e último start"]))
        elif state in ("CREATING",):
            ev = _ev(f"app {name} ainda {state}", 0.7)
            findings.append(Finding(
                category=FindingCategory.DEPENDENCY,
                severity=Severity.LOW,
                status=FindingStatus.POSSIBLE,
                explanation=f"Aplicação {name} ainda em {state} — "
                            "submissões podem falhar",
                evidence_ids=[ev.evidence_id]))

    def _job_run(self, j: dict[str, Any], _ev: Any,
                 findings: list[Finding], limitations: list[str]
                 ) -> None:
        jid = j.get("jobRunId") or j.get("id", "?")
        state = j.get("state", "")
        details = j.get("stateDetails", "")
        attempt = int(j.get("attempt", 1) or 1)
        created = j.get("createdAt")
        started_at = j.get("startedAt")

        if attempt > _RETRY_FLAG:
            ev = _ev(f"job {jid} attempt={attempt}", 0.9)
            findings.append(Finding(
                category=FindingCategory.TIMEOUT,
                severity=Severity.MEDIUM,
                status=FindingStatus.CONFIRMED,
                explanation=f"Job {jid} na tentativa {attempt} — "
                            "retry overhead (§4.6)",
                evidence_ids=[ev.evidence_id],
                validation_steps=["inspecionar falha da tentativa "
                                  "anterior"]))

        if isinstance(created, (int, float)) and isinstance(
                started_at, (int, float)):
            delay = started_at - created
            if delay > _SLOW_START_SECONDS:
                ev = _ev(f"job {jid} startup {delay:.0f}s", 0.8)
                findings.append(Finding(
                    category=FindingCategory.TIMEOUT,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.CONFIRMED,
                    explanation=f"Job {jid} levou {delay:.0f}s para "
                                "iniciar — slow startup (§4.6); "
                                "checar initialCapacity",
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "aumentar initialCapacity para warm pools",
                        "revisar maximumCapacity"]))

        if state == "FAILED":
            blob = details.lower()
            cat = FindingCategory.UNKNOWN
            if "outofmemory" in blob or "oom" in blob or \
                    "memory" in blob:
                cat = FindingCategory.OUT_OF_MEMORY
            elif "capacity" in blob:
                cat = FindingCategory.CONFIGURATION
            elif "role" in blob or "access" in blob:
                cat = FindingCategory.PERMISSIONS
            ev = _ev(f"job {jid} FAILED: {details[:160]}", 0.9)
            findings.append(Finding(
                category=cat, severity=Severity.HIGH,
                status=(FindingStatus.CONFIRMED
                        if cat != FindingCategory.UNKNOWN
                        else FindingStatus.PROBABLE),
                explanation=f"Job {jid} falhou: "
                            f"{details[:160] or 'sem stateDetails'}",
                evidence_ids=[ev.evidence_id],
                validation_steps=[
                    "coletar driver/executor logs via "
                    "monitoringConfiguration"],
                alternatives=[] if cat != FindingCategory.UNKNOWN
                else ["stateDetails não classificável — revisar "
                      "manualmente"]))
            if not j.get("monitoringConfiguration"):
                limitations.append(
                    f"job {jid}: monitoringConfiguration ausente — "
                    "logs podem estar indisponíveis")

        util = j.get("totalResourceUtilization") or {}
        vcpu = util.get("vCPUHour")
        if isinstance(vcpu, (int, float)) and vcpu > 0:
            # §4.5 — ESTIMATED, never billing
            est = vcpu * 0.052624 + float(
                util.get("memoryGBHour", 0) or 0) * 0.0057785
            ev = _ev(f"job {jid} uso {vcpu} vCPUh "
                     f"{util.get('memoryGBHour', 0)} GBh", 0.7)
            findings.append(Finding(
                category=FindingCategory.COST,
                severity=Severity.INFO,
                status=FindingStatus.PROBABLE,
                explanation=f"Job {jid}: ~{vcpu:.1f} vCPU-h declarados "
                            f"→ custo ESTIMADO ~US${est:.2f} "
                            "(us-east-1; não é billing real)",
                evidence_ids=[ev.evidence_id],
                alternatives=["billing real via CUR/Cost Explorer"]))
