"""Quality result adapters (ds-0042, §4).

Normalize EXPORTED results — never runs engines (Grill Gate).
Supported: PyDeequ/Deequ (AnalyzerContext JSON), Great Expectations
validation results, structured SQL results, DataFrame-style exports.

Preserves original metric names/values/units; missing result != pass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC
from typing import Any

from data_sentinel.core.contracts import (
    DatasetReference,
    ObservationStatus,
    QualityObservation,
    UTCDateTime,
)

ADAPTER_VERSION = "1.0.0"

_ADAPTERS: dict[str, AdapterDescriptor] = {}


@dataclass
class AdapterDescriptor:
    name: str
    version: str
    input_format: str
    available_fields: list[str]
    limitations: list[str]
    optional_dependencies: list[str] = field(default_factory=list)


def list_adapters() -> list[AdapterDescriptor]:
    return sorted(_ADAPTERS.values(), key=lambda a: a.name)


def _register(desc: AdapterDescriptor) -> None:
    _ADAPTERS[desc.name] = desc


def _ts(raw: Any) -> UTCDateTime | None:
    from datetime import datetime
    if not raw:
        return None
    try:
        s = str(raw).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except ValueError:
        return None


def _obs(oid: str, **kw: Any) -> QualityObservation:
    base: dict[str, Any] = {"observation_id": oid}
    base.update(kw)
    return QualityObservation.model_validate(base)


# --- PyDeequ / Deequ AnalyzerContext JSON --------------------------

_register(AdapterDescriptor(
    name="pydeequ",
    version=ADAPTER_VERSION,
    input_format="AnalyzerContext JSON / metrics map",
    available_fields=[
        "entity", "instance", "name", "value",
        "analyzer metadata (dataset/contextKey)"],
    limitations=[
        "semântica do Analyzer depende do runner; dataset pode ser "
        "inferido de contextKey",
        "valores de erro (Failure) viram UNKNOWN, nunca PASS"],
))

_DEEQU_STATUS = {"Success": ObservationStatus.PASS,
                 "Failure": ObservationStatus.FAIL}


def parse_pydeequ(raw: dict[str, Any], *, source: str = "") -> list[QualityObservation]:
    """Deequ AnalyzerContext map: {"<Entity>.<Instance>.<Metric>": value}
    or the metrics list shape [{entity, instance, name, value}]."""
    out: list[QualityObservation] = []
    metrics = raw.get("metrics", raw)
    if isinstance(metrics, dict):
        metrics = [{"name": k, "value": v} for k, v in metrics.items()]
    if not isinstance(metrics, list):
        return out
    for i, m in enumerate(metrics):
        if not isinstance(m, dict):
            continue
        name = m.get("name") or ""
        instance = m.get("instance") or ""
        value = m.get("value")
        err = m.get("error") or m.get("failure")
        status = ObservationStatus.UNKNOWN
        if isinstance(value, dict) and "Double" in value:
            value = value["Double"]
        if value is not None and not err:
            status = ObservationStatus.PASS  # engine emitted a value
        obs = _obs(
            f"pydeequ-{i}",
            rule_id=str(instance or name),
            observed_value=value,
            status=status if value is not None or err else
            ObservationStatus.UNKNOWN,
            source="pydeequ",
            metric_name=str(name),
            provenance=source,
            limitations=["valor bruto do Analyzer preservado; semântica "
                         "completa requer contexto do VerificationSuite"],
        )
        if err:
            obs = obs.model_copy(update={
                "status": ObservationStatus.UNKNOWN,
                "limitations": [*obs.limitations,
                    f"analyzer falhou: {err}"]})
        out.append(obs)
    return out


_register(AdapterDescriptor(
    name="deequ_checks",
    version=ADAPTER_VERSION,
    input_format="VerificationSuite checks JSON",
    available_fields=["status", "constraint_results[].status",
                      "constraint_results[].metric.value"],
    limitations=["constraint ids nem sempre batem com rule ids do "
                 "contrato — matching é por convenção"],
))


def parse_deequ_checks(raw: dict[str, Any],
                       *, source: str = "") -> list[QualityObservation]:
    """VerificationSuite check results: {checks: [{constraint, status}]}."""
    out: list[QualityObservation] = []
    for i, chk in enumerate(raw.get("checks") or []):
        status = _DEEQU_STATUS.get(str(chk.get("status", "")),
                                   ObservationStatus.UNKNOWN)
        for j, cr in enumerate(chk.get("constraint_results") or []):
            c = cr.get("constraint") or {}
            m = cr.get("metric") or {}
            cr_status = _DEEQU_STATUS.get(str(cr.get("status", "")),
                                          status)
            out.append(_obs(
                f"deequ-{i}-{j}",
                rule_id=str(c.get("id") or c.get("name") or j),
                observed_value=m.get("value"),
                status=cr_status,
                source="deequ",
                metric_name=str(m.get("name") or c.get("type") or ""),
                provenance=source,
            ))
    return out


# --- Great Expectations validation result --------------------------

_register(AdapterDescriptor(
    name="great_expectations",
    version=ADAPTER_VERSION,
    input_format="validation result JSON (ExpectationSuiteValidationResult)",
    available_fields=[
        "expectation_type", "kwargs", "result.observed_value",
        "success", "batch_identifiers", "run_id", "meta"],
    limitations=[
        "expectation_config parcial pode omitir kwargs",
        "unexpected_count nem sempre expõe observed_value numérico"],
))


def parse_ge(raw: dict[str, Any], *, source: str = "") -> list[QualityObservation]:
    out: list[QualityObservation] = []
    run_id = ""
    rid = raw.get("run_id") or raw.get("meta", {}).get("run_id")
    if isinstance(rid, dict):
        run_id = str(rid.get("run_name") or "")
    for i, res in enumerate(raw.get("results") or []):
        cfg = res.get("expectation_config") or {}
        etype = cfg.get("expectation_type") or cfg.get("type") or ""
        kw = cfg.get("kwargs") or {}
        resd = res.get("result") or {}
        val = resd.get("observed_value")
        if val is None:
            val = resd.get("unexpected_count")
        success = res.get("success")
        status = (ObservationStatus.PASS if success is True
                  else ObservationStatus.FAIL if success is False
                  else ObservationStatus.UNKNOWN)
        out.append(_obs(
            f"ge-{i}",
            rule_id=str(cfg.get("expectation_id") or etype or i),
            observed_value=val,
            expected_value=kw.get("expected_list") or kw.get(
                "value") or kw.get("min_value"),
            status=status,
            source="great_expectations",
            metric_name=str(etype),
            run_id=run_id,
            timestamp=_ts(raw.get("validation_time")
                          or res.get("validation_time")),
            provenance=source,
            limitations=["observed_value pode ser resumo estatístico "
                         "da GE, não medida bruta"],
        ))
    return out


# --- Structured SQL / DataFrame exports ----------------------------

_register(AdapterDescriptor(
    name="sql_results",
    version=ADAPTER_VERSION,
    input_format="JSON rows: [{rule_id, metric, value, expected, status}]",
    available_fields=["rule_id", "metric", "value", "expected",
                      "status", "timestamp", "run_id", "dataset"],
    limitations=["nomes de métricas e thresholds são responsabilidade "
                 "do produtor da query"],
))

_register(AdapterDescriptor(
    name="dataframe_export",
    version=ADAPTER_VERSION,
    input_format="JSON records com campos rule_id/value/expected",
    available_fields=["rule_id", "value", "expected", "column"],
    limitations=["amostras estatísticas (head) não provam volume total"],
))


def parse_rows(rows: list[dict[str, Any]], *, source: str,
               adapter: str) -> list[QualityObservation]:
    out: list[QualityObservation] = []
    for i, r in enumerate(rows):
        st = str(r.get("status") or "").upper()
        status = ObservationStatus(st) if st in ObservationStatus \
            .__members__ else ObservationStatus.UNKNOWN
        ds = r.get("dataset")
        out.append(_obs(
            f"{adapter}-{i}",
            rule_id=str(r.get("rule_id") or r.get("id") or i),
            dataset=DatasetReference.model_validate(ds) if isinstance(
                ds, dict) else None,
            observed_value=r.get("value") if "value" in r else
            r.get("observed_value"),
            expected_value=r.get("expected"),
            status=status,
            source=adapter,
            metric_name=str(r.get("metric") or ""),
            unit=str(r.get("unit") or ""),
            timestamp=_ts(r.get("timestamp")),
            run_id=str(r.get("run_id") or ""),
            provenance=source,
        ))
    return out


# --- dispatch -------------------------------------------------------

def normalize(raw: str, *, adapter: str = "auto",
              provenance: str = "") -> list[QualityObservation]:
    """Auto-detect format or force adapter; returns observations."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = None
    if data is None:
        import yaml
        data = yaml.safe_load(raw)
    if not isinstance(data, dict | list):
        return []

    if adapter == "auto":
        adapter = detect_adapter(data)
    if adapter == "auto":
        return []

    if adapter == "pydeequ":
        return parse_pydeequ(data if isinstance(data, dict) else
                             {"metrics": data}, source=provenance)
    if adapter == "deequ_checks":
        return parse_deequ_checks(data if isinstance(data, dict)
                                  else {"checks": data},
                                  source=provenance)
    if adapter == "great_expectations":
        return parse_ge(data if isinstance(data, dict) else
                        {"results": data}, source=provenance)
    if adapter == "sql_results":
        return parse_rows(data if isinstance(data, list) else
                          data.get("results") or data.get("rows") or [],
                          source=provenance, adapter="sql_results")
    if adapter == "dataframe_export":
        return parse_rows(data if isinstance(data, list) else
                          data.get("records") or data.get("rows") or [],
                          source=provenance,
                          adapter="dataframe_export")
    return []


def detect_adapter(data: Any) -> str:
    """Heuristic format detection — conservative, errs to 'auto'."""
    if isinstance(data, dict):
        if "expectation_config" in json.dumps(data.get("results")
                                            or [{}])[:4000]:
            return "great_expectations"
        if data.get("checks") and isinstance(data["checks"], list):
            return "deequ_checks"
        if data.get("metrics") or any("." in str(k) for k in
                                      list(data)[:5]):
            return "pydeequ"
        if data.get("results") or data.get("rows"):
            return "sql_results"
    if isinstance(data, list):
        return "sql_results"
    return "auto"
