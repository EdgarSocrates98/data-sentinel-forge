"""ds-0085 / §6 — cost intelligence: Glue DPU + what-if."""
from __future__ import annotations

from data_sentinel.analyzers.emr.cost import estimate_glue, what_if


class TestGlueEstimate:
    def test_g1x_basic(self):
        e = estimate_glue("G.1X", 10, 3600)
        assert e.amount is not None and e.confidence == "POSSIBLE"
        # 10 workers * 1 DPU * 1h * $0.44
        assert abs(e.amount - 4.4) < 0.01
        assert e.components["dpu_hours"] > 0

    def test_minimum_billing_60s(self):
        e = estimate_glue("G.1X", 2, 10)  # 10s < 60s floor
        assert e is not None
        # 2 workers * 1 DPU * (60/3600)h * 0.44 ≈ 0.0147
        assert 0.01 < e.amount < 0.02

    def test_flex_cheaper_but_not_declared_better(self):
        std = estimate_glue("G.1X", 10, 3600,
                            execution_class="STANDARD")
        flex = estimate_glue("G.1X", 10, 3600, execution_class="FLEX")
        assert flex.amount < std.amount
        assert any("não garantida" in a or "SLA" in a
                   for a in flex.assumptions)

    def test_retries_billed(self):
        no = estimate_glue("G.1X", 10, 3600)
        ret = estimate_glue("G.1X", 10, 3600, retries=2)
        assert ret.amount > no.amount
        assert any("retry" in a.lower() for a in ret.assumptions)

    def test_unknown_worker_type_not_invented(self):
        e = estimate_glue("X.99X", 10, 3600)
        assert e.amount is None and e.confidence == "UNKNOWN"

    def test_missing_inputs_unknown(self):
        e = estimate_glue(None, None, None)
        assert e.confidence == "UNKNOWN" and e.amount is None

    def test_exclusions_declared(self):
        e = estimate_glue("G.1X", 5, 600)
        assert e.exclusions and e.price_source


class TestWhatIf:
    def test_delta(self):
        base = estimate_glue("G.1X", 10, 3600)
        cand = estimate_glue("G.1X", 5, 3600)
        w = what_if("metade dos workers", base, cand)
        assert w.delta_amount is not None and w.delta_amount < 0
        assert w.delta_pct is not None and -60 < w.delta_pct < -40

    def test_never_claims_real_result(self):
        base = estimate_glue("G.1X", 10, 3600)
        w = what_if("h", base, base)
        assert any("não representa resultado real" in x
                   for x in w.limitations)

    def test_cross_platform_caveat(self):
        from data_sentinel.analyzers.emr.cost import estimate_serverless
        base = estimate_glue("G.1X", 10, 3600)
        cand = estimate_serverless(2.0)
        w = what_if("migrar", base, cand)
        assert any("plataformas distintas" in x
                   for x in w.limitations)

    def test_unknown_delta(self):
        base = estimate_glue("X.99X", 10, 3600)  # UNKNOWN
        cand = estimate_glue("G.1X", 5, 3600)
        w = what_if("h", base, cand)
        assert w.delta_amount is None
        assert any("UNKNOWN" in x for x in w.limitations)
