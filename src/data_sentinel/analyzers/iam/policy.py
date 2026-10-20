"""Offline IAM policy document analysis — §6.1, ds-0025.

Parses identity/resource/trust/boundary/session/SCP documents supplied as
JSON text. Evaluates whether a (action, resource) tuple is plausibly allowed
— never concludes "allowed" merely because an identity policy says Allow:
explicit denies, boundaries, SCPs, conditions and resource policies all
matter. Missing layers make the verdict UNKNOWN.
"""

import fnmatch
import json
from dataclasses import dataclass, field
from typing import Any


class PolicyParseError(ValueError):
    pass


@dataclass
class Statement:
    effect: str  # Allow | Deny
    actions: list[str]
    resources: list[str]
    principals: list[str]
    conditions: dict[str, Any]
    not_actions: list[str] = field(default_factory=list)
    not_resources: list[str] = field(default_factory=list)


@dataclass
class PolicyDoc:
    name: str
    statements: list[Statement]
    warnings: list[str] = field(default_factory=list)


def _listify(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]  # scalar (incl. tipos inesperados) → string, nunca descartado


def parse_policy(text: str, *, name: str = "policy") -> PolicyDoc:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PolicyParseError(f"{name}: JSON inválido: {exc}") from exc
    if not isinstance(raw, dict):
        raise PolicyParseError(f"{name}: policy deve ser objeto JSON")
    stmts_raw = raw.get("Statement")
    if not isinstance(stmts_raw, list):
        raise PolicyParseError(f"{name}: sem bloco 'Statement'")
    warnings: list[str] = []
    stmts: list[Statement] = []
    for i, st in enumerate(stmts_raw):
        if not isinstance(st, dict):
            warnings.append(f"{name}: statement {i} não é objeto — ignorado")
            continue
        effect = str(st.get("Effect", ""))
        if effect not in ("Allow", "Deny"):
            warnings.append(f"{name}: statement {i} Effect '{effect}' inválido")
            continue
        principals = _listify(st.get("Principal"))
        if isinstance(st.get("Principal"), dict):
            principals = [
                str(v) for vals in st["Principal"].values()
                for v in _listify(vals)
            ]
        stmts.append(
            Statement(
                effect=effect,
                actions=_listify(st.get("Action")),
                resources=_listify(st.get("Resource")),
                principals=principals,
                conditions=dict(st["Condition"]) if isinstance(st.get("Condition"), dict) else {},
                not_actions=_listify(st.get("NotAction")),
                not_resources=_listify(st.get("NotResource")),
            )
        )
    return PolicyDoc(name=name, statements=stmts, warnings=warnings)


def _matches(patterns: list[str], value: str) -> bool:
    return any(fnmatch.fnmatchcase(value.lower(), p.lower()) for p in patterns)


def stmt_covers(stmt: Statement, action: str, resource: str) -> bool:
    """Does this statement apply to (action, resource)?"""
    if stmt.actions and not _matches(stmt.actions, action):
        return False
    if stmt.not_actions and _matches(stmt.not_actions, action):
        return False
    if stmt.resources and not _matches(stmt.resources, resource):
        return False
    return not (stmt.not_resources and _matches(stmt.not_resources, resource))


@dataclass
class EvalResult:
    verdict: str  # allowed | denied | unknown
    reasons: list[str]
    matched_allows: int = 0
    matched_denies: int = 0


def evaluate(policies: list[PolicyDoc], action: str, resource: str) -> EvalResult:
    """Evaluate action+resource across supplied policy documents.

    Explicit deny anywhere wins. No matching allow → unknown (missing layers
    are listed, never assumed absent).
    """
    reasons: list[str] = []
    allows = denies = 0
    for pol in policies:
        for st in pol.statements:
            if not stmt_covers(st, action, resource):
                continue
            if st.effect == "Deny":
                denies += 1
                reasons.append(
                    f"{pol.name}: DENY explícito cobre {action} em {resource[:60]}"
                )
            else:
                if st.conditions:
                    reasons.append(
                        f"{pol.name}: Allow com Condition {sorted(st.conditions)} — "
                        "satisfação da condição não verificável offline"
                    )
                allows += 1
    if denies:
        return EvalResult("denied", reasons, allows, denies)
    if allows:
        reasons.append(
            "Allow existe, mas não prova acesso: boundaries, SCPs, resource "
            "policies e session policies não avaliáveis podem negar."
        )
        return EvalResult("allowed", reasons, allows, denies)
    reasons.append(
        f"Nenhum statement cobre {action} em {resource[:60]} — "
        "sem evidência de allow; ausência não prova negação "
        "(resource policies/roles não fornecidos)."
    )
    return EvalResult("unknown", reasons, allows, denies)
