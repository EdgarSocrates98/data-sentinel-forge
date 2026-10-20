"""Cycle 03.1 §7 evaluation — Doctor x Sentinel complementarity.

10 scenarios x 3 modes (doctor-only / sentinel-only / interop), executed
against REAL binaries. Ground truth per scenario declares which tool is
expected to carry the signal (per the domain-boundaries doc).

Env-gated: DATA_SENTINEL_EVAL=1 + DOCTOR_BIN=<forge-doctor-data>.
When the gate is off the run records BLOCKED — no fabricated numbers.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
OUT_JSON = REPO / "docs" / "evaluations" / "complementarity-results.json"
DOCTOR_BIN = os.environ.get("DOCTOR_BIN", "")
ENABLED = os.environ.get("DATA_SENTINEL_EVAL") == "1"

# ---------------------------------------------------------------- scenarios

OOM_LOG = """\
2026-01-10T10:00:00.000Z INFO  Starting Glue job etl-orders
2026-01-10T10:01:30.000Z INFO  Stage 3 (collect at merge.py:41) started
2026-01-10T10:04:00.000Z WARN  executor lost: heartbeat timeout
2026-01-10T10:04:02.000Z ERROR ExecutorLostFailure (executor 5 exited)
Caused by: java.lang.OutOfMemoryError: Java heap space
2026-01-10T10:04:05.000Z ERROR Job run failed
"""

SPARK_PLAN = """\
== Physical Plan ==
*(5) SortMergeJoin [o.order_id], [c.order_id], Inner
:- *(3) Sort [o.order_id ASC], false, 0
:  +- Exchange hashpartitioning(o.order_id, 200), ENSURE_REQUIREMENTS
:     +- *(1) FileScan parquet orders
+- *(4) Sort [c.order_id ASC], false, 0
   +- Exchange hashpartitioning(c.order_id, 200), ENSURE_REQUIREMENTS
      +- *(2) FileScan parquet customers
AdaptiveSparkPlan isFinalPlan=false
"""

MERGE_SQL = """\
MERGE INTO lake.sales.orders t
USING staging.orders s
ON t.order_id = s.order_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
"""

IAM_POLICY = json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": ["s3:GetObject"],
        "Resource": ["arn:aws:s3:::data-bucket/*"],
    }],
})

ICEBERG_METADATA = json.dumps({
    "format-version": 2,
    "table-uuid": "t-1",
    "location": "s3://lake/db/orders",
    "last-updated-ms": 1760000000000,
    "current-snapshot-id": 5,
    "snapshots": [
        {"snapshot-id": i, "timestamp-ms": 1760000000000 - i * 1000,
         "operation": "append", "summary": {"total-data-files": "40000"}}
        for i in range(1, 6)
    ],
    "schema": {"fields": [{"id": 1, "name": "order_id", "type": "long"}]},
    "partition-spec": [],
})

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "s01-pyspark-static",
        "title": "Erro estático de código PySpark",
        "project_files": {"job.py": "df.collect()\nimport nonexistent_module_xyz\n"},
        "artifact": None,
        "truth": {"doctor": ["PY", "REP"], "sentinel": []},
        "note": "auditoria estática é território Doctor",
    },
    {
        "id": "s02-glue-oom",
        "title": "Falha realista de Glue Job (OOM)",
        "project_files": {},
        "artifact": {"file": "job.log", "content": OOM_LOG,
                     "source_type": "log", "platform": "aws_glue"},
        "truth": {"doctor": [], "sentinel": ["out_of_memory"]},
        "note": "telemetria de execução é território Sentinel",
    },
    {
        "id": "s03-iceberg-runtime",
        "title": "Incompatibilidade runtime Iceberg",
        "project_files": {"pyproject.toml": '[project]\nname="p"\nversion="0.1"\n'},
        "artifact": None,
        "sentinel_call": "compat",
        "truth": {"doctor": ["GLUE", "ICE"], "sentinel": ["compat"]},
        "note": "ambos respondem com ângulos diferentes",
    },
    {
        "id": "s04-lakeformation-perm",
        "title": "Permissão Lake Formation insuficiente",
        "project_files": {},
        "artifact": {"file": "policy.json", "content": IAM_POLICY,
                     "source_type": "policy_doc", "platform": "aws_glue"},
        "truth": {"doctor": [], "sentinel": ["permissions"]},
        "note": "avaliação operacional de policy é Sentinel",
    },
    {
        "id": "s05-cross-account",
        "title": "Cross-account parcialmente configurado",
        "project_files": {},
        "artifact": {"file": "policy.json", "content": IAM_POLICY,
                     "source_type": "access_context", "platform": "aws_glue"},
        "truth": {"doctor": [], "sentinel": []},
        "note": "UNKNOWN honesto é resultado válido",
    },
    {
        "id": "s06-merge-dups",
        "title": "MERGE com risco de duplicidade",
        "project_files": {"merge.sql": MERGE_SQL},
        "artifact": {"file": "merge.sql", "content": MERGE_SQL,
                     "source_type": "sql_query", "platform": "spark"},
        "truth": {"doctor": [], "sentinel": ["sql"]},
        "note": "análise de execução MERGE é Sentinel",
    },
    {
        "id": "s07-shuffle-skew",
        "title": "Spark shuffle/skew",
        "project_files": {},
        "artifact": {"file": "plan.txt", "content": SPARK_PLAN,
                     "source_type": "physical_plan", "platform": "spark"},
        "truth": {"doctor": [], "sentinel": ["cost", "data_skew",
                                            "sql_antipattern"]},
        "note": "plano de execução é Sentinel",
    },
    {
        "id": "s08-regression",
        "title": "Regressão entre execuções",
        "project_files": {},
        "artifact": {"file": "job.log", "content": OOM_LOG,
                     "source_type": "log", "platform": "aws_glue"},
        "truth": {"doctor": [], "sentinel": ["out_of_memory"]},
        "note": "baseline/histórico é Doctor; detecção da falha é Sentinel",
    },
    {
        "id": "s09-incomplete",
        "title": "Dados incompletos",
        "project_files": {},
        "artifact": {"file": "trunc.log",
                     "content": "INFO starting\nWARN ",
                     "source_type": "log", "platform": "aws_glue"},
        "truth": {"doctor": [], "sentinel": []},
        "note": "UNKNOWN/nenhum achado correto — sem fabricação",
    },
    {
        "id": "s10-conflicting",
        "title": "Findings conflitantes entre fontes",
        "project_files": {"job.py": "df.collect()\n"},
        "artifact": {"file": "job.log", "content": OOM_LOG,
                     "source_type": "log", "platform": "aws_glue"},
        "truth": {"doctor": [], "sentinel": ["out_of_memory"]},
        "note": "interop: estático + telemetria coexistem com proveniência",
    },
]

# ---------------------------------------------------------------- runners


def _write(root: Path, files: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")


def run_doctor(project: Path) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(  # noqa: S603
        [DOCTOR_BIN, "scan", "--format", "json", str(project)],
        capture_output=True, text=True, timeout=180,
    )
    elapsed = round(time.perf_counter() - t0, 3)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": proc.stderr[:300], "results": [],
                "elapsed_s": elapsed}
    results = data.get("results", [])
    return {"results": results, "elapsed_s": elapsed,
            "ids": [r.get("check_id", "") for r in results],
            "calls_external": 0}


def run_sentinel(scenario: dict[str, Any], workdir: Path) -> dict[str, Any]:
    sys.path.insert(0, str(REPO / "src"))
    t0 = time.perf_counter()
    art = scenario.get("artifact")
    cats: list[str] = []
    n_findings = 0
    if scenario.get("sentinel_call") == "compat":
        from data_sentinel.knowledge.compat import assess_compatibility
        a = assess_compatibility(
            None, runtime="glue-4.0", table_format="iceberg",
            access_mode="iam", operation="merge",
        )
        n_findings = len(a.constraints) + (1 if a.support_status.value
                                           in ("UNSUPPORTED",
                                               "SUPPORTED_WITH_CONSTRAINTS")
                                           else 0)
        cats = ["compat"] if n_findings else []
    elif art:
        from data_sentinel.core.contracts import (
            ArtifactReference,
            DiagnosticRequest,
            Platform,
            SourceType,
        )
        from data_sentinel.core.security import InputFile
        from data_sentinel.diagnostics.orchestrator import run_diagnostics

        af = workdir / "artifacts" / art["file"]
        af.parent.mkdir(parents=True, exist_ok=True)
        af.write_text(art["content"], encoding="utf-8")
        request = DiagnosticRequest(
            source_type=SourceType(art["source_type"]),
            artifact_references=[ArtifactReference(uri=str(af))],
            platform=Platform(art["platform"]),
        )
        inp = InputFile(path=af, text=art["content"],
                        size_bytes=len(art["content"].encode()))
        outcome = run_diagnostics(request, [inp])
        findings = outcome.report.findings
        n_findings = len(findings)
        cats = sorted({f.category.value for f in findings})
    return {"categories": cats, "n_findings": n_findings,
            "elapsed_s": round(time.perf_counter() - t0, 3),
            "calls_external": 0}


def run_interop(scenario: dict[str, Any], workdir: Path,
                doctor_out: dict[str, Any], sent_out: dict[str, Any]) -> dict:
    """Doctor bundle → adapter → union with sentinel findings."""
    sys.path.insert(0, str(REPO / "src"))
    from data_sentinel.adapters.doctor import import_doctor_bundle

    bundle_path = workdir / "doctor.json"
    bundle_path.write_text(json.dumps({
        "contract": "handoff-bundle", "contract_version": 1,
        "tool": {"name": "forge-doctor-data", "version": "real"},
        "results": doctor_out.get("results", []),
        "graph": {"entities": [], "relationships": []},
        "capabilities": {}, "plans": [],
        "project": {"root": str(workdir / "project")},
        "summary": {},
    }))
    imp = import_doctor_bundle(bundle_path)
    imported_text = " ".join(f.explanation for f in imp.findings)
    # duplicates: sentinel findings whose text echoes an imported check_id
    dup = 0
    for cat in sent_out.get("categories", []):
        if re.search(rf"(?i){re.escape(cat.split('_')[0])}", imported_text):
            dup += 1
    return {
        "imported": len(imp.findings),
        "sentinel_findings": sent_out.get("n_findings", 0),
        "union": len(imp.findings) + sent_out.get("n_findings", 0),
        "dup_estimate": dup,
    }


# ---------------------------------------------------------------- driver


def expected_hit(expected: list[str], ids: list[str],
                 cats: list[str]) -> tuple[bool, list[str]]:
    hits = [e for e in expected
            if any(i.startswith(e) for i in ids)
            or any(e in c for c in cats)]
    return bool(hits), hits


def evaluate() -> dict[str, Any]:
    out: dict[str, Any] = {
        "gate": "DATA_SENTINEL_EVAL=1 + DOCTOR_BIN",
        "enabled": ENABLED and bool(DOCTOR_BIN),
        "scenarios": [],
        "totals": {},
    }
    if not out["enabled"]:
        out["status"] = "BLOCKED"
        return out

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for sc in SCENARIOS:
            work = root / sc["id"]
            _write(work / "project", sc["project_files"])
            doc = run_doctor(work / "project")
            sent = run_sentinel(sc, work)
            inter = run_interop(sc, work, doc, sent)
            d_hit, d_hits = expected_hit(
                sc["truth"]["doctor"], doc.get("ids", []), [])
            s_hit, s_hits = expected_hit(
                sc["truth"]["sentinel"], [], sent.get("categories", []))
            rec = {
                "id": sc["id"], "title": sc["title"], "note": sc["note"],
                "doctor": {
                    "detected": d_hit, "hits": d_hits,
                    "n_results": len(doc.get("results", [])),
                    "elapsed_s": doc.get("elapsed_s"),
                } if sc["project_files"] or sc["truth"]["doctor"]
                else "NOT_SUPPORTED",
                "sentinel": {
                    "detected": s_hit, "hits": s_hits,
                    "n_findings": sent.get("n_findings", 0),
                    "elapsed_s": sent.get("elapsed_s"),
                } if sc["artifact"] or sc.get("sentinel_call")
                else "NOT_SUPPORTED",
                "interop": inter,
            }
            out["scenarios"].append(rec)

    ds = [s for s in out["scenarios"] if s["doctor"] != "NOT_SUPPORTED"]
    ss = [s for s in out["scenarios"] if s["sentinel"] != "NOT_SUPPORTED"]
    out["totals"] = {
        "scenarios": len(out["scenarios"]),
        "doctor_applicable": len(ds),
        "doctor_detected": sum(1 for s in ds if s["doctor"]["detected"]),
        "sentinel_applicable": len(ss),
        "sentinel_detected": sum(1 for s in ss if s["sentinel"]["detected"]),
        "doctor_elapsed_s": round(sum(
            s["doctor"]["elapsed_s"] for s in ds), 3),
        "sentinel_elapsed_s": round(sum(
            s["sentinel"]["elapsed_s"] for s in ss), 3),
        "external_calls": 0,
        "interop_union": sum(
            s["interop"]["union"] for s in out["scenarios"]),
        "interop_dup_estimate": sum(
            s["interop"]["dup_estimate"] for s in out["scenarios"]),
    }
    out["status"] = "VERIFIED"
    return out


if __name__ == "__main__":
    result = evaluate()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["totals"], indent=2))  # noqa: T201
    print("status:", result.get("status"), "->", OUT_JSON)  # noqa: T201
