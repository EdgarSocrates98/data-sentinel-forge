"""Declarative quality contract loading + static validation (§3.2-3.5).

Accepts YAML or JSON in the §3.2 shape:

    contract_version: "1.0"
    dataset: analytics.customer_events
    rules:
      - id: customer_id_not_null
        type: completeness
        column: customer_id
        expected: 1.0
        severity: high

Security: file size cap, safe YAML loader (never unsafe_load), no eval,
strict envelope. Validation reports issues — never executes rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from data_sentinel.core.contracts import (
    DataQualityContract,
    DatasetReference,
    FreshnessPolicy,
    QualityRule,
    RuleType,
)

MAX_CONTRACT_BYTES = 1_048_576  # 1 MB
MAX_RULES = 5_000
_SEVERITIES = {"info", "low", "medium", "high", "critical"}


class ContractFormatError(ValueError):
    """Unparseable or structurally invalid contract file."""


@dataclass
class ContractIssue:
    field: str
    message: str
    severity: str = "error"  # error | warning


@dataclass
class ContractValidation:
    contract: DataQualityContract | None
    issues: list[ContractIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.contract is not None and not any(
            i.severity == "error" for i in self.issues
        )


def _load_envelope(text: str) -> dict[str, Any]:
    if len(text.encode()) > MAX_CONTRACT_BYTES:
        raise ContractFormatError(
            f"contract exceeds {MAX_CONTRACT_BYTES} bytes")
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ContractFormatError(f"YAML inválido: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContractFormatError("contrato deve ser um objeto/mapping")
    return raw


def _parse_dataset(raw: Any) -> DatasetReference:
    if isinstance(raw, str):
        parts = raw.split(".")
        if len(parts) >= 2:
            return DatasetReference(namespace=".".join(parts[:-1]),
                                    name=parts[-1])
        return DatasetReference(namespace="", name=raw)
    if isinstance(raw, dict):
        return DatasetReference.model_validate(raw)
    raise ContractFormatError("dataset deve ser string ou objeto")


def _parse_rule(raw: Any, idx: int) -> QualityRule:
    if not isinstance(raw, dict):
        raise ContractFormatError(f"regra #{idx} deve ser um objeto")
    rid = raw.get("id") or raw.get("rule_id") or f"rule-{idx}"
    rtype_raw = str(raw.get("type") or raw.get("rule_type") or "")
    try:
        rtype = RuleType(rtype_raw)
    except ValueError as exc:
        raise ContractFormatError(
            f"regra '{rid}': type desconhecido '{rtype_raw}' "
            f"(válidos: {sorted(r.value for r in RuleType)})") from exc
    cols = raw.get("columns")
    target = raw.get("column") or (
        "+".join(str(c) for c in cols) if isinstance(cols, list) and cols
        else str(cols) if cols else raw.get("target") or "dataset"
    )
    params = {k: v for k, v in raw.items()
              if k not in {"id", "rule_id", "type", "rule_type", "column",
                           "columns", "target", "expected", "severity",
                           "tolerance", "parameters"}}
    params.update(raw.get("parameters") or {})
    return QualityRule(
        rule_id=str(rid),
        rule_type=rtype,
        target=str(target),
        expected=raw.get("expected"),
        tolerance=raw.get("tolerance"),
        severity=str(raw.get("severity") or "medium"),
        parameters=params,
    )


def parse_contract_text(text: str, *, provenance: str = "") -> DataQualityContract:
    """Parse §3.2 YAML/JSON into DataQualityContract (strict envelope)."""
    raw = _load_envelope(text)
    rules_raw = raw.get("rules") or raw.get("quality_rules") or []
    if not isinstance(rules_raw, list):
        raise ContractFormatError("rules deve ser uma lista")
    if len(rules_raw) > MAX_RULES:
        raise ContractFormatError(f"regras excedem {MAX_RULES}")
    rules = [_parse_rule(r, i) for i, r in enumerate(rules_raw)]

    freshness = raw.get("freshness_policy") or raw.get("freshness")
    fp = None
    if isinstance(freshness, dict):
        fp = FreshnessPolicy(
            max_age_seconds=freshness.get("max_age_seconds")
            or freshness.get("max_age"),
            reference_field=str(freshness.get("reference_field") or ""),
        )

    try:
        return DataQualityContract(
            contract_id=str(raw.get("contract_id")
                            or raw.get("id") or "contract"),
            version=str(raw.get("contract_version")
                        or raw.get("version") or "1.0"),
            dataset=_parse_dataset(raw.get("dataset")),
            schema_fields=raw.get("schema") or {},
            constraints=raw.get("constraints") or [],
            quality_rules=rules,
            freshness_policy=fp,
            owner=str(raw.get("owner") or ""),
            provenance=provenance or str(raw.get("provenance") or ""),
        )
    except ValidationError as exc:
        raise ContractFormatError(f"contrato inválido: {exc}") from exc


def load_contract(path: Path) -> DataQualityContract:
    if not path.is_file():
        raise ContractFormatError(f"não é arquivo: {path}")
    if path.stat().st_size > MAX_CONTRACT_BYTES:
        raise ContractFormatError(
            f"contrato excede {MAX_CONTRACT_BYTES} bytes")
    return parse_contract_text(
        path.read_text(encoding="utf-8"), provenance=str(path))


def validate_contract(contract: DataQualityContract) -> ContractValidation:
    """Static semantic validation — types, targets, tolerances, dup ids."""
    issues: list[ContractIssue] = []
    seen: set[str] = set()
    for r in contract.quality_rules:
        if r.rule_id in seen:
            issues.append(ContractIssue(
                field=f"rules.{r.rule_id}",
                message="rule_id duplicado"))
        seen.add(r.rule_id)
        if r.severity.lower() not in _SEVERITIES:
            issues.append(ContractIssue(
                field=f"rules.{r.rule_id}.severity",
                message=f"severidade inválida '{r.severity}'"))
        if r.rule_type in (RuleType.COMPLETENESS, RuleType.UNIQUENESS,
                           RuleType.UNIQUENESS_RATIO):
            if r.expected is not None and not isinstance(
                    r.expected, int | float):
                issues.append(ContractIssue(
                    field=f"rules.{r.rule_id}.expected",
                    message="expected deve ser numérico (razão 0-1)"))
            elif isinstance(r.expected, int | float) and not (
                    0 <= float(r.expected) <= 1):
                issues.append(ContractIssue(
                    field=f"rules.{r.rule_id}.expected",
                    message="razão esperada fora de [0,1]",
                    severity="warning"))
        if (contract.schema_fields and r.target not in ("dataset",)
                and "+" not in r.target
                and r.target not in contract.schema_fields):
            issues.append(ContractIssue(
                field=f"rules.{r.rule_id}.target",
                message=f"coluna '{r.target}' não está no schema do "
                        "contrato",
                severity="warning"))
    if not contract.quality_rules:
        issues.append(ContractIssue(
            field="rules", message="contrato sem regras",
            severity="warning"))
    return ContractValidation(contract=contract, issues=issues)
