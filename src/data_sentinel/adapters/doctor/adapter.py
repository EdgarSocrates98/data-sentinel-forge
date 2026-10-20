"""Doctor bundle → Sentinel internals.

Import-only direction (Grill Gate ds-0030..0039 #1). Imported findings
keep external provenance and are never auto-CONFIRMED.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from data_sentinel.core.contracts import (
    Evidence,
    EvidenceProvenance,
    ExternalDiagnosticBundle,
    Finding,
    FindingCategory,
    FindingStatus,
    InteropFinding,
    Severity,
    ToolRef,
)
from data_sentinel.core.security import redact_secrets

MAX_BUNDLE_BYTES = 20 * 1024 * 1024
MAX_FINDINGS = 10_000

FORMAT_HANDOFF_LEGACY = "handoff-bundle@1"
FORMAT_FORGE_CONTRACTS_1 = "forge-contracts/1"
FORMAT_SCAN_JSON_3 = "scan-json@3.0"

_SEVERITY = {
    "pass": Severity.INFO,
    "info": Severity.INFO,
    "low": Severity.LOW,
    "warning": Severity.MEDIUM,
    "medium": Severity.MEDIUM,
    "error": Severity.HIGH,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
    "INFO": Severity.INFO,
}

# imported findings: confidence → certainty (never CONFIRMED)
_STATUS = {
    "high": FindingStatus.PROBABLE,
    "medium": FindingStatus.POSSIBLE,
    "low": FindingStatus.POSSIBLE,
    "unknown": FindingStatus.UNKNOWN,
    "UNKNOWN": FindingStatus.UNKNOWN,
}

_CONFIDENCE = {"high": 0.8, "medium": 0.5, "low": 0.3, "unknown": 0.0}

_CATEGORY = {
    "security": FindingCategory.SECURITY,
    "apisec": FindingCategory.SECURITY,
    "dependencies": FindingCategory.DEPENDENCY,
    "sql": FindingCategory.SQL_ANTIPATTERN,
    "quality": FindingCategory.DATA_QUALITY,
    "cost": FindingCategory.COST,
    "compatibility": FindingCategory.COMPATIBILITY,
    "lakeformation": FindingCategory.PERMISSIONS,
    "iam": FindingCategory.PERMISSIONS,
    "configuration": FindingCategory.CONFIGURATION,
}


class DoctorBundleError(ValueError):
    """Raised when a file is not a recognizable/valid Doctor bundle."""


def detect_bundle_format(raw: dict[str, Any]) -> str:
    """Detect which real Doctor output shape this payload is."""
    if not isinstance(raw, dict):
        raise DoctorBundleError("bundle root must be a JSON object")
    if raw.get("contract") == "handoff-bundle" and "results" in raw:
        return FORMAT_HANDOFF_LEGACY
    if raw.get("contract_version") == "forge-contracts/1" or (
        "findings" in raw and isinstance(raw.get("findings"), list)
    ):
        return FORMAT_FORGE_CONTRACTS_1
    if raw.get("schema_version") == "3.0" and "results" in raw:
        return FORMAT_SCAN_JSON_3
    raise DoctorBundleError(
        "unrecognized Doctor bundle: expected handoff-bundle, "
        "forge-contracts/1 findings, or scan schema_version 3.0"
    )


def load_doctor_file(path: Path) -> dict[str, Any]:
    """Read + parse a bundle file offline; size-capped; never executes."""
    if not path.is_file():
        raise DoctorBundleError(f"not a file: {path}")
    size = path.stat().st_size
    if size > MAX_BUNDLE_BYTES:
        raise DoctorBundleError(f"bundle exceeds {MAX_BUNDLE_BYTES} bytes")
    if size == 0:
        raise DoctorBundleError("empty bundle file")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DoctorBundleError(f"malformed JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise DoctorBundleError("bundle root must be a JSON object")
    return raw


def _normalize(raw: dict[str, Any], fmt: str) -> ExternalDiagnosticBundle:
    tool = raw.get("tool") or {}
    producer = ToolRef(
        name=str(tool.get("name") or "forge-doctor"),
        version=tool.get("version"),
    )
    project = raw.get("project") or {}
    source_refs: list[str] = []
    if isinstance(project.get("root"), str):
        source_refs.append(redact_secrets(project["root"]))
    if fmt == FORMAT_FORGE_CONTRACTS_1:
        caps = raw.get("capabilities") or []
        if isinstance(caps, dict):  # legacy map shape
            caps = [
                {"id": f"{dom}.{cap}", "domain": dom, "status": st}
                for dom, entries in caps.items()
                for cap, st in (entries or {}).items()
            ]
        bundle = ExternalDiagnosticBundle(
            contract_version=raw.get("contract_version"),
            producer=producer,
            generated_at=raw.get("generated_at"),
            source_references=source_refs,
            findings=raw.get("findings") or [],
            entities=raw.get("entities") or [],
            relationships=raw.get("relationships") or [],
            capabilities=caps,
            unknowns=raw.get("unknowns") or [],
            plans=raw.get("plans") or [],
            project=project,
            summary=raw.get("summary") or {},
        )
    else:
        graph = raw.get("graph") or {}
        caps = raw.get("capabilities") or {}
        bundle = ExternalDiagnosticBundle(
            contract_version=raw.get("contract_version"),
            producer=producer,
            generated_at=raw.get("generated_at"),
            source_references=source_refs,
            findings=raw.get("results") or [],
            entities=graph.get("entities") or [],
            relationships=graph.get("relationships") or [],
            capabilities=[
                {"id": f"{dom}.{cap}", "domain": dom, "status": st}
                for dom, entries in caps.items()
                for cap, st in (entries or {}).items()
            ] if isinstance(caps, dict) else caps,
            plans=raw.get("plans") or [],
            project=project,
            summary=raw.get("summary") or {},
        )
    if len(bundle.findings) > MAX_FINDINGS:
        bundle.findings = bundle.findings[:MAX_FINDINGS]
        bundle.limitations.append(
            f"bundle truncated at {MAX_FINDINGS} findings"
        )
    return bundle


def _finding_timestamp(bundle: ExternalDiagnosticBundle, fallback: float) -> datetime:
    if bundle.generated_at:
        try:
            dt = datetime.fromisoformat(bundle.generated_at.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.fromtimestamp(fallback, tz=UTC)


def _to_internal(
    item: InteropFinding,
    bundle: ExternalDiagnosticBundle,
    captured: datetime,
    idx: int,
) -> tuple[Finding, Evidence | None]:
    fid = item.external_id
    text = redact_secrets(item.text)[:2000] or "(sem descrição no bundle)"
    producer = bundle.producer.name
    loc = item.file or (item.source_location if hasattr(item, "source_location") else None)

    evidence: Evidence | None = None
    evidence_ids: list[str] = []
    raw_ev = item.evidence
    excerpt = text
    if isinstance(raw_ev, str) and raw_ev:
        excerpt = redact_secrets(raw_ev)[:2000]
    elif isinstance(raw_ev, list) and raw_ev:
        first = raw_ev[0]
        excerpt = redact_secrets(
            first if isinstance(first, str) else (first.detail or first.ref or "")
        )[:2000]
    content_hash = hashlib.sha256(
        json.dumps(item.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()
    evidence = Evidence(
        source=f"{producer}:{bundle.producer.version or 'unknown'}",
        source_location=redact_secrets(loc or f"bundle://{producer}/{fid}"),
        captured_at=captured,
        content_hash=content_hash,
        sanitized_excerpt=excerpt or "(sem excerpt)",
        provenance=EvidenceProvenance.DECLARED,
        confidence=_CONFIDENCE.get(str(item.confidence or "unknown").lower(), 0.0),
    )
    evidence_ids.append(evidence.evidence_id)

    status = _STATUS.get(str(item.confidence or "unknown"), FindingStatus.UNKNOWN)
    if item.confidence is None:
        status = FindingStatus.UNKNOWN
    category = _CATEGORY.get((item.category or "").lower(), FindingCategory.UNKNOWN)

    recs: list[str] = []
    for r in (item.recommendation, item.remediation):
        if r:
            recs.append(redact_secrets(r)[:1000])
    sev = _SEVERITY.get(str(item.severity or "info"), Severity.INFO)

    finding = Finding(
        category=category,
        severity=sev,
        status=status,
        explanation=(
            f"[importado:{producer}] [{fid}] {text}"
            + (f" (fingerprint={item.fingerprint})" if item.fingerprint else "")
            + (f" (desconhecidos: {len(item.unknowns)})" if item.unknowns else "")
        )[:4000],
        evidence_ids=evidence_ids,
        recommendations=recs,
    )
    return finding, evidence


@dataclass
class ImportedDiagnostics:
    """Result of importing a Doctor bundle."""

    bundle: ExternalDiagnosticBundle
    format: str
    findings: list[Finding] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def import_doctor_bundle(path: Path) -> ImportedDiagnostics:
    """Full pipeline: load → detect → normalize → internal findings."""
    raw = load_doctor_file(path)
    fmt = detect_bundle_format(raw)
    bundle = _normalize(raw, fmt)
    bundle.integrity = bundle.integrity or None
    captured = _finding_timestamp(bundle, path.stat().st_mtime)

    result = ImportedDiagnostics(bundle=bundle, format=fmt)
    for idx, item in enumerate(bundle.findings):
        finding, evidence = _to_internal(item, bundle, captured, idx)
        result.findings.append(finding)
        if evidence is not None:
            result.evidence.append(evidence)
    if bundle.unknowns:
        result.warnings.append(
            f"{len(bundle.unknowns)} fatos desconhecidos preservados do produtor"
        )
    return result
