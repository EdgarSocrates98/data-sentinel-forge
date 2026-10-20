"""EMR cost & capacity intelligence (ds-0065, §8).

Static versioned price table (us-east-1 baseline, Grill Gate) —
declared assumptions, never billing. Missing usage → UNKNOWN verdict,
not a fake zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# us-east-1, EMR-6.x/Serverless published rates — versioned snapshot.
# Region/price drift is declared in `price_source`.
PRICES: dict[str, dict[str, float]] = {
    "emr-serverless": {"vcpu_hour": 0.052624,
                       "mem_gb_hour": 0.0057785,
                       "storage_gb_hour": 0.000111},
    "emr-ec2": {"emr_markup_m5xlarge_hour": 0.048,  # EMR surcharge
                "ec2_m5xlarge_hour": 0.192,
                "ebs_gb_month": 0.10},
    "emr-eks": {"emr_vcpu_hour": 0.01012,
                "emr_gb_hour": 0.00111125,
                "eks_cluster_hour": 0.10},
    "glue": {"dpu_hour_standard": 0.44,
             "dpu_hour_flex": 0.29,
             "min_billable_seconds": 60.0},
}
# Glue worker type -> DPUs por worker (Glue 2.0+, AWS docs).
GLUE_WORKER_DPU: dict[str, float] = {
    "standard": 1.0, "g.025x": 0.25, "g.1x": 1.0, "g.2x": 2.0,
    "g.4x": 4.0, "g.8x": 8.0, "g.12x": 12.0, "g.16x": 16.0,
    "r.1x": 1.0, "r.2x": 2.0, "r.4x": 4.0, "r.8x": 8.0,
    "z.1x": 1.0, "z.2x": 2.0,
}
PRICE_SOURCE = "static-table-2025-01,us-east-1"
CURRENCY = "USD"


@dataclass
class CostEstimate:
    platform: str
    region: str = "us-east-1"
    currency: str = CURRENCY
    window_hours: float | None = None
    billing_model: str = "on_demand"
    usage_source: str = "declared"
    price_source: str = PRICE_SOURCE
    amount: float | None = None           # None → UNKNOWN
    components: dict[str, float] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    confidence: str = "POSSIBLE"

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _unk(platform: str, why: str) -> CostEstimate:
    return CostEstimate(platform=platform, amount=None,
                        confidence="UNKNOWN",
                        exclusions=[f"dados ausentes: {why}"])


def estimate_serverless(vcpu_hours: float | None,
                        mem_gb_hours: float | None = None,
                        storage_gb_hours: float | None = None,
                        *, region: str = "us-east-1") -> CostEstimate:
    p = PRICES["emr-serverless"]
    if vcpu_hours is None:
        return _unk("emr_serverless", "vCPU-hour não declarado")
    comp = {"vcpu": vcpu_hours * p["vcpu_hour"]}
    if mem_gb_hours is not None:
        comp["memory"] = mem_gb_hours * p["mem_gb_hour"]
    if storage_gb_hours is not None:
        comp["storage"] = storage_gb_hours * p["storage_gb_hour"]
    return CostEstimate(
        platform="emr_serverless", region=region,
        amount=round(sum(comp.values()), 4), components=comp,
        assumptions=["preços us-east-1; descontos/Savings Plan "
                     "não aplicáveis a EMR Serverless"],
        exclusions=["egress", "S3 requests", "CloudWatch"],
        confidence="POSSIBLE")


def estimate_ec2(instance_type: str | None, count: int | None,
                 hours: float | None, *,
                 region: str = "us-east-1") -> CostEstimate:
    if not instance_type or count is None or hours is None:
        return _unk("emr_ec2",
                    "instance_type/count/horas não declarados")
    p = PRICES["emr-ec2"]
    ec2_rate = p.get(f"ec2_{instance_type.lower()}_hour")
    if ec2_rate is None:
        return CostEstimate(
            platform="emr_ec2", region=region, amount=None,
            confidence="UNKNOWN",
            exclusions=[f"preço EC2 para '{instance_type}' fora da "
                        "tabela — sem estimativa em vez de inventar"])
    markup = p.get(f"emr_markup_{instance_type.lower()}_hour", 0.0)
    comp = {"ec2": count * hours * ec2_rate,
            "emr_markup": count * hours * markup}
    return CostEstimate(
        platform="emr_ec2", region=region,
        amount=round(sum(comp.values()), 4), components=comp,
        assumptions=["on-demand; spot/RI alteram o valor real",
                     "EBS não incluído sem volumes declarados"],
        exclusions=["EBS", "egress", "EMRFS consistent view",
                    "bootstrap actions"],
        confidence="POSSIBLE")


def estimate_eks(vcpu_hours: float | None,
                 mem_gb_hours: float | None = None,
                 cluster_hours: float | None = None,
                 *, region: str = "us-east-1") -> CostEstimate:
    p = PRICES["emr-eks"]
    if vcpu_hours is None:
        return _unk("emr_eks", "vCPU-hour não declarado")
    comp = {"emr_vcpu": vcpu_hours * p["emr_vcpu_hour"]}
    if mem_gb_hours is not None:
        comp["emr_memory"] = mem_gb_hours * p["emr_gb_hour"]
    if cluster_hours is not None:
        comp["eks_control_plane"] = (cluster_hours
                                     * p["eks_cluster_hour"])
    return CostEstimate(
        platform="emr_eks", region=region,
        amount=round(sum(comp.values()), 4), components=comp,
        assumptions=["compute EC2/Fargate dos nós NÃO incluído — "
                     "cobrança separada"],
        exclusions=["EC2/Fargate nodes", "EBS", "network",
                    "observability"],
        confidence="POSSIBLE")


def cost_recommendations(estimates: list[CostEstimate]
                         ) -> list[str]:
    """§8.5 — never recommends without SLA/perf caveat."""
    recs: list[str] = []
    for e in estimates:
        if e.amount is None:
            recs.append(f"{e.platform}: coletar uso real antes de "
                        "estimar (dados ausentes declarados)")
        elif e.platform == "emr_ec2":
            recs.append("avaliar mix spot/on-demand e idle-time "
                        "considerando SLA do workload antes de "
                        "mudanças")
        elif e.platform == "emr_serverless":
            recs.append("revisar retries e initialCapacity — "
                        "otimizar custo sem degradar SLA")
        else:
            recs.append("separar custo EMR de custo de nós EKS "
                        "antes de otimizar — sem trocar por menor "
                        "sem validar desempenho")
    return recs


def estimate_glue(worker_type: str | None, workers: int | None,
                  duration_seconds: float | None, *,
                  execution_class: str = "STANDARD",
                  retries: int = 0,
                  region: str = "us-east-1") -> CostEstimate:
    """§6.1 — DPU-hour billing estimate. Observado ≠ cobrança real."""
    if worker_type is None or workers is None or duration_seconds is None:
        return _unk("glue", "worker_type/workers/duração não declarados")
    dpu_per = GLUE_WORKER_DPU.get(worker_type.lower())
    if dpu_per is None:
        return CostEstimate(
            platform="glue", region=region, amount=None,
            confidence="UNKNOWN",
            exclusions=[f"worker_type '{worker_type}' fora da tabela "
                        "DPU — sem estimativa em vez de inventar"])
    p = PRICES["glue"]
    billable_s = max(duration_seconds, p["min_billable_seconds"])
    hours = billable_s / 3600.0
    total_workers = workers * (1 + max(0, retries))
    dpu_hours = total_workers * dpu_per * hours
    is_flex = execution_class.upper() == "FLEX"
    rate = p["dpu_hour_flex"] if is_flex else p["dpu_hour_standard"]
    comp = {"dpu_hours": round(dpu_hours, 4),
            "compute": round(dpu_hours * rate, 4)}
    assumptions = ["on-demand; billing mínimo 60s por execução (Glue 2.0+)"]
    if retries:
        assumptions.append(f"{retries} retry(ies) cobrados como "
                           "execuções adicionais")
    if is_flex:
        assumptions.append("FLEX: menor custo, execução não garantida "
                           "— não declarar 'mais barato' sem SLA")
    return CostEstimate(
        platform="glue", region=region,
        amount=round(comp["compute"], 4), components=comp,
        billing_model="flex" if is_flex else "on_demand",
        assumptions=assumptions,
        exclusions=["job queuing/wait time não faturado",
                    "observability", "S3 requests", "egress",
                    "interactive sessions", "Data Quality charges"],
        confidence="POSSIBLE")


@dataclass
class WhatIfResult:
    """§6.6 — comparação de cenários; NUNCA afirma resultado real."""
    hypothesis: str
    baseline: CostEstimate
    candidate: CostEstimate
    delta_amount: float | None = None
    delta_pct: float | None = None
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"hypothesis": self.hypothesis,
                "baseline": self.baseline.to_dict(),
                "candidate": self.candidate.to_dict(),
                "delta_amount": self.delta_amount,
                "delta_pct": self.delta_pct,
                "limitations": list(self.limitations)}


def what_if(hypothesis: str, baseline: CostEstimate,
            candidate: CostEstimate) -> WhatIfResult:
    lims = [
        "simulação não representa resultado real de execução",
        "duração sob outro dimensionamento é desconhecida — "
        "assumida constante salvo declaração explícita",
    ]
    if baseline.platform != candidate.platform:
        lims.append("plataformas distintas — comparação de custo não "
                    "implica equivalência de desempenho/SLA")
    res = WhatIfResult(hypothesis=hypothesis, baseline=baseline,
                       candidate=candidate, limitations=lims)
    if (baseline.amount is not None and candidate.amount is not None
            and baseline.amount > 0):
        res.delta_amount = round(candidate.amount - baseline.amount, 4)
        res.delta_pct = round(100.0 * res.delta_amount
                              / baseline.amount, 2)
    else:
        res.limitations.append("delta indisponível — baseline ou "
                               "candidato UNKNOWN")
    return res
