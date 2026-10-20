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
