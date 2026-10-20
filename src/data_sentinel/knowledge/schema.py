"""Compatibility knowledge base — rule schema, loading, validation (§8).

Rules are YAML package resources (`knowledge/rules/*.yaml`) shipped inside
the wheel — never resolved from the repository checkout. Every rule carries
source/version/date/owner provenance; schema-invalid rules fail validation.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from importlib import resources
from typing import Any

import yaml

from data_sentinel.core.contracts.enums import SupportStatus

_RULE_PACKAGE = "data_sentinel.knowledge.rules"

_REQUIRED = {
    "rule_id": str,
    "version": str,
    "service": str,
    "status": str,
    "references": list,
    "last_verified": str,
    "owner": str,
    "reviewer": str,
}
_MATCH_KEYS = ("service", "engine", "runtime", "table_format", "operation",
               "catalog", "access_mode")


class RuleValidationError(ValueError):
    """A rule file failed schema validation."""


@dataclass(frozen=True)
class Rule:
    rule_id: str
    version: str
    service: str
    status: SupportStatus
    references: list[str]
    last_verified: str
    owner: str
    reviewer: str
    engine: str = ""
    runtime: str = ""
    table_format: str = ""
    operation: str = ""
    catalog: str = ""
    access_mode: str = ""
    constraints: str = ""
    conditions: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)

    def matches(self, ctx: dict[str, str]) -> bool:
        """All declared match keys must equal the context (empty = wildcard)."""
        for key in _MATCH_KEYS:
            want = getattr(self, key)
            if want and want != "*" and ctx.get(key, "") != want:
                return False
        return all(ctx.get(key, "") == str(want) for key, want in self.conditions.items())

    @property
    def specificity(self) -> int:
        """More declared match keys + conditions = more specific rule wins.

        Wildcard "*" does not add specificity — it matches everything.
        """
        return (
            sum(1 for k in _MATCH_KEYS if getattr(self, k) not in ("", "*"))
            + len(self.conditions)
        )


def validate_rule(raw: dict[str, Any], *, source: str) -> list[str]:
    """Return validation errors (empty = valid). Never raises."""
    errors: list[str] = []
    for key, typ in _REQUIRED.items():
        if key not in raw:
            errors.append(f"{source}: campo obrigatório ausente '{key}'")
        elif not isinstance(raw[key], typ):
            errors.append(f"{source}: '{key}' deve ser {typ.__name__}")
    status = raw.get("status")
    if isinstance(status, str) and status not in {s.value for s in SupportStatus}:
        errors.append(f"{source}: status '{status}' inválido")
    if not raw.get("references"):
        errors.append(f"{source}: regra sem fonte/referência não é admitida")
    if not isinstance(raw.get("history", []), list):
        errors.append(f"{source}: 'history' deve ser lista")
    return errors


def _to_rule(raw: dict[str, Any]) -> Rule:
    return Rule(
        rule_id=str(raw["rule_id"]),
        version=str(raw["version"]),
        service=str(raw["service"]),
        status=SupportStatus(str(raw["status"])),
        references=[str(r) for r in raw["references"]],
        last_verified=str(raw["last_verified"]),
        owner=str(raw["owner"]),
        reviewer=str(raw["reviewer"]),
        engine=str(raw.get("engine", "")),
        runtime=str(raw.get("runtime", "")),
        table_format=str(raw.get("table_format", "")),
        operation=str(raw.get("operation", "")),
        catalog=str(raw.get("catalog", "")),
        access_mode=str(raw.get("access_mode", "")),
        constraints=str(raw.get("constraints", "")),
        conditions=dict(raw.get("conditions") or {}),
        history=list(raw.get("history") or []),
    )


def load_rules(yaml_texts: Iterable[tuple[str, str]]) -> tuple[list[Rule], list[str]]:
    """Parse (source_name, yaml_text) pairs → (rules, errors)."""
    rules: list[Rule] = []
    errors: list[str] = []
    for name, text in yaml_texts:
        try:
            docs = list(yaml.safe_load_all(text))
        except yaml.YAMLError as exc:
            errors.append(f"{name}: YAML inválido: {exc}")
            continue
        for raw in docs:
            if raw is None:
                continue
            items = raw if isinstance(raw, list) else [raw]
            for item in items:
                if not isinstance(item, dict):
                    errors.append(f"{name}: documento não é objeto YAML")
                    continue
                errs = validate_rule(item, source=name)
                errors.extend(errs)
                if not errs:
                    rules.append(_to_rule(item))
    # duplicate rule_id = conflict flagged at load time
    seen: set[str] = set()
    for r in rules:
        if r.rule_id in seen:
            errors.append(f"rule_id duplicado: {r.rule_id}")
        seen.add(r.rule_id)
    return rules, errors


def load_packaged_rules() -> tuple[list[Rule], list[str]]:
    """Load rules shipped inside the wheel via importlib.resources."""
    texts: list[tuple[str, str]] = []
    root = resources.files(_RULE_PACKAGE)
    for entry in root.iterdir():
        if entry.name.endswith((".yaml", ".yml")):
            texts.append((entry.name, entry.read_text(encoding="utf-8")))
    return load_rules(texts)
