"""IamPolicyAnalyzer — §6, ds-0025.

Analyzes IAM policy documents + optional S3/KMS context supplied as inputs
(source_type=POLICY_DOC). Produces evidence-backed hypotheses for
AccessDenied without claiming root cause when layers are missing.
Optionally accepts a JSON envelope: {"policy": {...}, "context": {...},
"evaluate": [{"action": "...", "resource": "..."}]} — a bare policy document
is accepted too.
"""

import hashlib
import json
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from data_sentinel.analyzers.iam.policy import (
    PolicyDoc,
    PolicyParseError,
    evaluate,
    parse_policy,
)
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

_EvFn = Callable[..., Evidence]

_S3_ACTIONS = ("s3:",)
_KMS_ACTIONS = ("kms:",)


class IamPolicyAnalyzer(Analyzer):
    @property
    def analyzer_id(self) -> str:
        return "iam.policy"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def supported_platforms(self) -> tuple[str, ...]:
        return (Platform.AWS_GLUE, Platform.ATHENA)

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (SourceType.POLICY_DOC,)

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
            "Análise offline de policies — SCPs, permission boundaries, "
            "resource policies e session policies só contam se fornecidos",
            "IAM SimulatePrincipalPolicy é opcional e NÃO usada por "
            "padrão; suas limitações (resource policies, SCPs, contexto "
            "de sessão, Lake Formation) estão documentadas — simulação "
            "não é validação real",
            "Conditions de policy não são avaliadas — Allow condicional "
            "permanece hipótese",
            "Decrypt nunca é executado como teste",
        )

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=list(self.supported_platforms),
            supported_runtimes=["glue-4.0", "glue-5.0", "glue-5.1"],
            required_permissions=["filesystem:read"],
            supported_operations=["analyze_iam_policy"],
            limitations=list(self.limitations),
        )

    def analyze(self, request: DiagnosticRequest, inputs: Sequence[InputFile]) -> AnalysisResult:
        started = time.monotonic()
        captured = datetime.now(UTC)
        self.validate_input(request, inputs)

        findings: list[Finding] = []
        evidence: list[Evidence] = []
        limitations: list[str] = list(self.limitations)
        evals_meta: list[dict[str, object]] = []

        for input_file in inputs:
            digest = hashlib.sha256(input_file.text.encode()).hexdigest()

            def _ev(snippet: str, conf: float = 0.7,
                    _p: str = str(input_file.path), _d: str = digest) -> Evidence:
                ev = Evidence(
                    source="policy_doc",
                    source_location=_p,
                    captured_at=captured,
                    content_hash=_d,
                    sanitized_excerpt=sanitize_evidence_excerpt(snippet, max_chars=500),
                    provenance=EvidenceProvenance.DECLARED,
                    confidence=conf,
                )
                evidence.append(ev)
                return ev

            docs, evals, ctx, err = self._load(input_file)
            if err:
                limitations.append(f"{input_file.path}: {err}")
                continue
            for d in docs:
                for w in d.warnings:
                    limitations.append(f"{input_file.path}: {w}")
            self._static(docs, _ev, findings, limitations)
            if ctx:
                self._context(ctx, _ev, findings, limitations)
            for q in evals:
                self._eval_one(docs, q, _ev, findings, evals_meta)

        if not findings:
            findings.append(
                Finding(
                    category=FindingCategory.UNKNOWN,
                    severity=Severity.INFO,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        "Policies analisadas sem achados — isso NÃO prova "
                        "acesso: camadas não fornecidas podem negar."
                    ),
                    evidence_ids=[],
                )
            )

        return AnalysisResult(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.version,
            request_id=request.request_id,
            findings=findings,
            evidence=evidence,
            limitations=limitations,
            metadata={"evaluations": evals_meta},
            duration_ms=int((time.monotonic() - started) * 1000),
            analyzed_at=captured,
        )

    # ------------------------------------------------------------------

    def _load(
        self, f: InputFile,
    ) -> tuple[list[PolicyDoc], list[dict[str, object]], dict[str, object] | None, str | None]:
        """→ (docs, eval_queries, ctx, error)."""
        try:
            raw = json.loads(f.text)
        except json.JSONDecodeError as exc:
            return [], [], None, f"policy não é JSON: {exc}"
        if not isinstance(raw, dict):
            return [], [], None, "policy deve ser objeto JSON"

        if "Statement" in raw:  # bare policy
            try:
                return [parse_policy(f.text, name=str(f.path))], [], None, None
            except PolicyParseError as exc:
                return [], [], None, str(exc)

        docs: list[PolicyDoc] = []
        policies = raw.get("policies") or {}
        if isinstance(raw.get("policy"), dict):
            policies = {str(f.path): raw["policy"], **policies}
        if not isinstance(policies, dict) or not policies:
            return [], [], None, "envelope sem 'policy'/'policies'"
        for name, doc in policies.items():
            try:
                docs.append(parse_policy(json.dumps(doc), name=name))
            except PolicyParseError as exc:
                return [], [], None, str(exc)
        evals = [q for q in raw.get("evaluate", []) if isinstance(q, dict)
                 and q.get("action")]
        ctx = raw.get("context") if isinstance(raw.get("context"), dict) else None
        return docs, evals, ctx, None

    def _static(
        self, docs: list[PolicyDoc], _ev: _EvFn,
        findings: list[Finding], limitations: list[str],
    ) -> None:
        for d in docs:
            allows_wild = [s for s in d.statements
                           if s.effect == "Allow" and "*" in s.actions]
            denies = [s for s in d.statements if s.effect == "Deny"]
            cond_allows = [s for s in d.statements
                           if s.effect == "Allow" and s.conditions]
            if allows_wild:
                ev = _ev(f"{d.name}: {len(allows_wild)} Allow(s) com Action='*'")
                findings.append(
                    Finding(
                        category=FindingCategory.SECURITY,
                        severity=Severity.LOW,
                        status=FindingStatus.CONFIRMED,
                        explanation=(
                            f"Policy '{d.name}' contém Action='*' — superfície "
                            "ampla; não implica acesso (denies/boundaries "
                            "podem restringir) mas amplia blast radius."
                        ),
                        evidence_ids=[ev.evidence_id],
                        recommendations=["Escopar Action para serviços/recursos necessários."],
                    )
                )
            if cond_allows:
                _ev(f"{d.name}: {len(cond_allows)} Allow(s) condicionais "
                    f"({[sorted(s.conditions) for s in cond_allows][:3]})",
                    conf=0.6)
            if not denies and not allows_wild:
                limitations.append(
                    f"{d.name}: sem Deny explícito nem wildcard — cobertura "
                    "aparentemente mínima"
                )

    def _context(
        self, ctx: dict[str, object], _ev: _EvFn,
        findings: list[Finding], limitations: list[str],
    ) -> None:
        """S3/KMS declared context — hypotheses only, no calls."""
        bucket = ctx.get("bucket")
        if (
            isinstance(bucket, dict)
            and bucket.get("cross_account")
            and not bucket.get("policy_visible")
        ):
                findings.append(
                Finding(
                    category=FindingCategory.PERMISSIONS,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        f"Bucket cross-account '{bucket.get('name', '?')}' "
                            "sem bucket policy visível — ownership/policy/"
                            "Object Ownership não verificáveis."
                        ),
                        recommendations=[
                            "Exportar GetBucketPolicy/GetBucketAcl da conta "
                            "proprietária para verificar grants."
                        ],
                    )
                )
        kms = ctx.get("kms")
        if isinstance(kms, dict):
            src, dst = kms.get("source_key"), kms.get("dest_key")
            if src and dst and src != dst:
                ev = _ev(
                    f"KMS source key {src[:50]} != dest key {dst[:50]} — "
                    "cenário de duas chaves",
                )
                findings.append(
                    Finding(
                        category=FindingCategory.PERMISSIONS,
                        severity=Severity.MEDIUM,
                        status=FindingStatus.POSSIBLE,
                        explanation=(
                            "Chaves KMS diferentes origem/destino — leitura "
                            "exige Decrypt na origem e escrita exige "
                            "GenerateDataKey/Encrypt no destino; grants e "
                            "key policies das DUAS contas devem existir."
                        ),
                        evidence_ids=[ev.evidence_id],
                        recommendations=[
                            "Verificar key policies + grants nas duas contas; "
                            "AccessDenied KMS costuma vir do par origem/destino."
                        ],
                    )
                )
            if kms.get("key_policy_visible") is False:
                limitations.append(
                    "Key policy KMS não visível — cadeia de autorização "
                    "incompleta, não negação."
                )

    def _eval_one(
        self, docs: list[PolicyDoc], q: dict[str, object], _ev: _EvFn,
        findings: list[Finding], meta: list[dict[str, object]],
    ) -> None:
        action = str(q["action"])
        resource = str(q.get("resource", "*"))
        res = evaluate(docs, action, resource)
        meta.append({"action": action, "resource": resource,
                     "verdict": res.verdict})
        ev = _ev(f"eval {action} em {resource[:60]} → {res.verdict}; "
                 f"allows={res.matched_allows} denies={res.matched_denies}; "
                 + "; ".join(res.reasons[:2]))
        if res.verdict == "denied":
            findings.append(
                Finding(
                    category=FindingCategory.PERMISSIONS,
                    severity=Severity.HIGH,
                    status=FindingStatus.CONFIRMED,
                    explanation=(
                        f"Deny explícito cobre '{action}' em '{resource[:60]}' — "
                        "deny vence qualquer allow."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=["Remover/estreitar o Deny ou isentar o principal."],
                )
            )
        elif res.verdict == "allowed":
            findings.append(
                Finding(
                    category=FindingCategory.PERMISSIONS,
                    severity=Severity.INFO,
                    status=FindingStatus.POSSIBLE,
                    explanation=(
                        f"Allow cobre '{action}', mas acesso NÃO está provado: "
                        "camadas não fornecidas (boundary/SCP/resource policy/"
                        "session) podem negar."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Confirmar com SimulatePrincipalPolicy (limitações "
                        "documentadas) ou CloudTrail da falha real."
                    ],
                )
            )
        else:
            findings.append(
                Finding(
                    category=FindingCategory.PERMISSIONS,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        f"Nenhuma policy fornecida cobre '{action}' em "
                        f"'{resource[:60]}' — hipótese de AccessDenied por "
                        "ausência de grant, não prova (outras policies podem existir)."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Fornecer identity+resource policies relevantes ou "
                        "consultar CloudTrail para o erro observado."
                    ],
                )
            )
