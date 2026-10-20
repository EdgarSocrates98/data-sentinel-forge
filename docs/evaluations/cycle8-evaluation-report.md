# Cycle 08 §5 — Benchmarks & Evaluation Report

Spec: `ds-0094` · Dataset: `fixtures/evals/cycle7/` (30 golden scenarios)
· Harness: `tests/evaluation/run_cycle8_eval.py` · Raw data:
`cycle8-results.json`

- **Git SHA**: `62f4e812f0c41fe6aa36f0869900c08039e10031`
- **Generated**: 2026-10-20T15:40:15Z (real run — no fabricated numbers)
- **Environment**: Python 3.12.3, Linux, offline (external calls: **0**)
- **Code path**: identical to the golden test —
  `tests.e2e.test_cycle7_golden.run_scenario`

All 30 scenarios were executed through the golden runner. Verdicts:
**tp=13, fp=1, fn=1, tn=10, delegated=6**. Finding-level metrics:
**precision 0.9286** (13/14), **recall 0.9286** (13/14),
**correct UNKNOWN emissions: 5**, **unsupported claims: 1**,
**literal forbidden-phrase violations: 0**. Overall latency
p50 = 0.081 ms, p95 = 47.85 ms.

## Per-domain metrics (measured)

| domain | scen. | exec. | tp | fp | fn | tn | unk.✓ | precision | recall | evid. cov. | unsup. claims | forbid. | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| regressions | 7 | 7 | 2 | 0 | 1 | 4 | 1 | 1.000 | 0.667 | 100% (2/2) | 0 | 0 | 0.127 | 0.158 |
| spark | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 1.000 | 1.000 | 0% (0/4) | 0 | 0 | 47.85 | 669.2 |
| emr | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 1.000 | 1.000 | 100% (6/6) | 0 | 0 | 3.56 | 6.62 |
| iceberg | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1.000 | 1.000 | 50% (1/2) | **1** | 0 | 6.65 | 6.65 |
| alerting | 3 | 3 | 2 | 1 | 0 | 1 | 0 | 0.667 | 1.000 | n/a¹ | 0 | 0 | 0.183 | 0.379 |
| watch | 2 | 2 | 0 | 0 | 0 | 2 | 0 | n/a | n/a | n/a¹ | 0 | 0 | 0.021 | 0.064 |
| quality | 1 | 1 | 0 | 0 | 0 | 1 | 0 | n/a | n/a | n/a¹ | 0 | 0 | 0.068 | 0.068 |
| agent-runtime | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1.000 | 1.000 | n/a | 0 | 0 | 0.195 | 0.195 |
| remediation | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1.000 | 1.000 | n/a | 0 | 0 | 0.008 | 0.008 |
| interop | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1.000 | 1.000 | n/a | 0 | 0 | 5.02 | 5.02 |
| cost | 1 | 1 | 0 | 0 | 0 | 1 | 1 | n/a | n/a | n/a | 0 | 0 | 5.69 | 5.69 |
| comparison | 1 | 1 | 0 | 0 | 0 | 1 | 1 | n/a | n/a | n/a | 0 | 0 | 0.008 | 0.008 |
| persistence | 2 | 0² | — | — | — | — | — | n/a | n/a | n/a | 0 | 0 | 0.002 | 0.003 |
| streaming-sse | 2 | 0² | — | — | — | — | — | n/a | n/a | n/a | 0 | 0 | 0.001 | 0.001 |
| concurrency | 1 | 0² | — | — | — | — | — | n/a | n/a | n/a | 0 | 0 | 0.001 | 0.001 |
| api-security | 1 | 0² | — | — | — | — | — | n/a | n/a | n/a | 0 | 0 | 0.003 | 0.003 |
| agent-routing³ | 10 cases | 10 | 10 | 0 | 0 | — | — | 1.000 | 1.000 | n/a | 0 | 0 | — | — |

¹ Alert objects exported by the golden runner carry only
`kind`/`recovered` — evidence is not inspectable on that surface.
² Delegated to `tests/e2e/test_cycle7_ops.py` — same code path as the
golden test; the harness records them as delegated, not measured.
³ Measured from `tests/evals/agentic_evals.json` (6/6) +
`emr_evals.json` (4/4) — deterministic `route()` accuracy, not a
finding-level metric. Combined accuracy **10/10 = 1.0**.

## §5.1 spec-domain coverage

| §5.1 domain | coverage |
|---|---|
| Spark plans | spark-oom, partial-evidence, shuffle-regression |
| SQL optimization | **no scenarios — not measured** |
| Glue failures | job-failure, duration-regression |
| EMR diagnostics | emr-serverless-delay, emr-ec2-idle, emr-eks-scheduling |
| Iceberg | iceberg-small-files |
| Lake Formation | **no scenarios — not measured** |
| IAM | **no scenarios — not measured** (unauthorized-api covers API bearer auth, not IAM policy analysis) |
| Quality | quality-degradation |
| Lineage | **no scenarios — not measured** |
| Root Cause | conflicting-observations, doctor-bundle-correlation (honesty-level only; dedicated RCA engine not scenario-tested) |
| Agent routing | token-budget + routing eval sets (10 cases) |
| MCP | **no scenarios — not measured** |
| Watch | freshness-violation, watch-disabled |
| Alerting | job-failure, alert-dedup, alert-recovery |
| Regressions | duration-regression, volume-growth, shuffle-regression, incomplete-metrics, conflicting-observations, false-positive-regression, seasonal-workload |

## Deterministic vs Agentic (§5.3)

Deterministic = `investigate()` pipeline alone. Agentic = same pipeline
+ one bounded `AgentRuntime` task calling **StubProvider** to draft a
synthesis (the repo's only offline provider; `economy`/`balanced`/`deep`
profiles route to `LocalProvider` at localhost:11434, which was **not
contacted** — those profiles are not measured here).

| scenario | det. findings | det. tokens | det. ms | agentic findings | agentic tokens | agentic ms | agentic state |
|---|---|---|---|---|---|---|---|
| spark-oom | 2 | 0 | 3.73 | 2 | 26 | 3.86 | completed |
| emr-serverless-delay | 4 | 0 | 3.69 | 4 | 26 | 3.66 | completed |
| emr-ec2-idle | 1 | 0 | 2.89 | 1 | 26 | 2.91 | completed |
| emr-eks-scheduling | 1 | 0 | 5.84 | 1 | 26 | 5.91 | completed |
| iceberg-small-files | 2 | 0 | 7.16 | 2 | 26 | 7.76 | completed |
| partial-evidence | 2 | 0 | 4.54 | 2 | 26 | 4.78 | completed |
| **totals / p50 / p95** | | **0** | **3.73 / 7.16** | | **156** | **3.86 / 7.76** | |

Measured: agentic adds **26 tokens/scenario** (156 total) with
**cost_usd = 0.00** — StubProvider has no pricing model, so this is
*absence of a cost model*, not free inference. Latency deltas are
within noise (~ms). Findings identical — **no quality improvement is
claimed**: the stub is a deterministic echo, so this measures agentic
loop overhead only. Token/cost/latency fields are read off
`InvestigationReport` (`tokens_used`, `cost_usd`, `duration_seconds`).

## Measured findings worth attention

1. **`volume-growth` — real false negative.** The fixture declares
   `baseline_bytes`/`current_bytes`, which the golden runner's
   regression branch does not map onto `input_bytes` snapshots — the
   inputs never reach `detect_regressions`, so no signal is produced.
   Fixture↔runner schema gap, surfaced honestly as recall loss.
2. **`iceberg-small-files` — 1 unsupported claim.** The analyzer emits
   a `CONFIRMED` finding ("60 entradas de snapshot-log — listagens de
   catálogo ficam mais caras") with an empty `evidence_ids` — a real
   contract violation (CONFIRMED requires evidence) that the golden
   test's lenient assertion did not catch.
3. **`alert-recovery` — 1 false positive.** The recovery alert is
   correctly emitted, but an extra `missing_data` alert fires for the
   metricless recovery snapshot — a legitimate honesty signal, yet
   outside the expected set (counted, not hidden).
4. **`quality-degradation` / `freshness-violation` — silent
   non-detection.** `dq_pass_rate` and `freshness_s` are not in the
   regression `SIGNALS` tuple (`quality_score`/`data_freshness_s` are),
   so the watch engine emits neither alert nor declaration. The
   scenario contracts permit this ("or declared", "evaluated"), so both
   score tn — but the coverage gap is real: metric names in fixtures
   do not reach the detector.
5. **Spark analyzer scenarios emit all-UNKNOWN findings with 0%
   evidence coverage.** `fixtures/golden/spark-oom.json` and
   `fixtures/logs/spark_exception.log` are not parseable Spark plans —
   the analyzer degrades honestly (UNKNOWN + 7 declared limitations)
   rather than fabricating. Correct behavior; the evidence-coverage
   number reflects it.

## Limitations (honest)

- 6/30 scenarios (persistence, SSE, concurrency, auth) are delegated to
  `tests/e2e/test_cycle7_ops.py` — the golden runner does not exercise
  them, so this harness measures nothing there beyond dispatch latency.
- Evidence coverage is measurable only where the runner surface
  exports evidence (regression dicts, analyzer findings); watch alerts
  export `kind`/`recovered` only.
- Forbidden phrases are descriptive Portuguese text, not literal output
  markers — literal substring violations are ~0 by construction; the
  meaningful check is the unsupported-claim counter (CONFIRMED/proven
  without evidence), which caught the iceberg finding above.
- Latency is single-shot `perf_counter` (no warmup repeats); p95 on
  n<5 domains ≈ max. Spark analyzer (~0.04–0.7 s) dominates — file I/O
  + plan parsing.
- `peak_memory_kb` is per-scenario traced allocation above baseline
  (tracemalloc), not RSS.
- economy/balanced/deep profiles and real-LLM quality are unmeasured:
  no local model endpoint in this environment, and none was contacted.
- §5.1 domains with zero golden scenarios (SQL optimization, Lake
  Formation, IAM, Lineage, MCP) are explicitly marked "not measured" —
  extending coverage is a fixture-authoring task, not a code change.
