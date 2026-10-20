"""ds-0028 — Cycle 03 benchmarks (§10.4). Representative metadata only."""

import json
import time
import tracemalloc
from pathlib import Path

from data_sentinel.analyzers.iam import evaluate, parse_policy
from data_sentinel.analyzers.iceberg import parse_metadata
from data_sentinel.knowledge import load_packaged_rules, select

OUT = Path("docs/evidence/benchmarks-cycle3.json")
RES: dict[str, dict] = {}


def _rec(name: str, **kv):
    RES.setdefault(name, {}).update(kv)


def _big_meta(n_snaps: int) -> str:
    return json.dumps({
        "format-version": 2,
        "schemas": [{"schema-id": 0, "type": "struct", "fields": [
            {"id": i, "name": f"f{i}", "required": False, "type": "string"}
            for i in range(50)]}],
        "snapshots": [
            {"snapshot-id": i, "parent-snapshot-id": i - 1 or None,
             "timestamp-ms": 1700000000000 + i, "operation": "append",
             "manifest-list": f"s3://b/m/s{i}.avro",
             "summary": {"added-data-files": "10",
                         "added-files-size": str(80 * 1024 * 1024)}}
            for i in range(1, n_snaps + 1)],
        "snapshot-log": [{"snapshot-id": i, "timestamp-ms": i}
                         for i in range(1, n_snaps + 1)],
    })


def test_metadata_parse_scaling():
    for n in (100, 1000, 5000):
        doc = _big_meta(n)
        t0 = time.monotonic()
        m = parse_metadata(doc)
        dt = time.monotonic() - t0
        assert len(m.snapshots) == n
        _rec("metadata_parse", **{f"snapshots_{n}": round(dt, 4)})


def test_metadata_parse_memory():
    doc = _big_meta(5000)
    tracemalloc.start()
    parse_metadata(doc)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    _rec("metadata_parse", peak_bytes_5000_snaps=peak,
         input_bytes=len(doc.encode()))


def test_rule_load_and_select():
    t0 = time.monotonic()
    rules, errors = load_packaged_rules()
    load_dt = time.monotonic() - t0
    assert errors == []
    ctx = {"service": "aws_glue", "engine": "spark", "runtime": "glue-5.1",
           "table_format": "iceberg"}
    t0 = time.monotonic()
    for _ in range(10000):
        select(rules, ctx)
    _rec("knowledge", rules=len(rules), load_s=round(load_dt, 4),
         select_10k_s=round(time.monotonic() - t0, 4))


def test_policy_eval_scaling():
    doc = '{"Statement":[' + ",".join(
        '{"Effect":"Allow","Action":"s3:*","Resource":"arn:aws:s3:::b'
        + str(i) + '/*"}'
        for i in range(500)) + "]}"
    d = parse_policy(doc)
    t0 = time.monotonic()
    for _ in range(1000):
        evaluate([d], "s3:GetObject", "arn:aws:s3:::b250/x")
    _rec("iam_eval", statements=len(d.statements),
         eval_1000_s=round(time.monotonic() - t0, 4))


def test_report_latency_lakehouse():
    from data_sentinel.analyzers.protocol import InputFile
    from data_sentinel.analyzers.registry import registry
    from data_sentinel.core.contracts.entities import ArtifactReference, DiagnosticRequest
    from data_sentinel.core.contracts.enums import Platform, SourceType
    p = Path("fixtures/iceberg/v2_evolved.json")
    t = p.read_text()
    req = DiagnosticRequest(
        source_type=SourceType.ICEBERG_METADATA,
        artifact_references=[ArtifactReference(uri="x")],
        platform=Platform.AWS_GLUE)
    inp = InputFile(path=p, text=t, size_bytes=len(t.encode()))
    a = registry.get("iceberg.metadata")
    t0 = time.monotonic()
    for _ in range(100):
        a.analyze(req, [inp])
    _rec("analyzer", iceberg_analyze_100_s=round(time.monotonic() - t0, 4))


def test_dump_results():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"cycle": 3, "results": RES}, indent=2))
    assert OUT.exists()
