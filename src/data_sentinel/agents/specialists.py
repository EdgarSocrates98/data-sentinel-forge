"""Specialist agents (ds-0057, §5).

Deterministic-first specialists: each wraps tool-registry calls, never
calls an LLM by default. The Coordinator plans tasks across them.
"""

from __future__ import annotations

from data_sentinel.core.contracts.agent import AgentDescriptor, AgentTask

# (agent_id, name, responsibility, allowed_tools)
_SPECIALISTS: list[tuple[str, str, str, list[str]]] = [
    ("coordinator", "Sentinel Coordinator",
     "plan investigation, delegate, synthesize", []),
    ("spark-expert", "Spark Performance Expert",
     "spark plans, OOM, skew, config tuning",
     ["sentinel.spark.analyze_plan", "sentinel.spark.optimize"]),
    ("glue-expert", "AWS Glue Expert",
     "Glue job runs, driver/executor failures",
     ["sentinel.glue.inspect_run", "sentinel.glue.diagnose_run"]),
    ("iceberg-expert", "Iceberg Expert",
     "metadata, snapshots, small files, evolution",
     ["sentinel.iceberg.inspect_metadata",
      "sentinel.iceberg.analyze_operation"]),
    ("lakeformation-expert", "Lake Formation Expert",
     "access assessment, FGAC, resource links",
     ["sentinel.lakeformation.assess_access"]),
    ("sql-expert", "SQL Expert",
     "query antipatterns, joins, stats",
     ["sentinel.sql.analyze"]),
    ("quality-expert", "Data Quality Expert",
     "contracts, drift, validation results",
     ["sentinel.quality.assess", "sentinel.quality.detect_drift"]),
    ("lineage-expert", "Data Lineage Expert",
     "lineage graph, impact analysis",
     ["sentinel.lineage.ingest", "sentinel.lineage.impact"]),
    ("root-cause-analyst", "Root Cause Analyst",
     "cluster findings into ranked hypotheses", []),
    ("evidence-validator", "Evidence Validator",
     "independent validation of findings", []),
    ("security-reviewer", "Security Reviewer",
     "IAM/policy/security finding review",
     ["sentinel.iam.analyze_policy"]),
    ("report-specialist", "Report Specialist",
     "structured investigation report", []),
    # §9 — EMR specialization (ds-0066)
    ("emr-coordinator", "EMR Coordinator",
     "identify EMR modality, select experts, manage budget", []),
    ("emr-ec2-expert", "EMR EC2 Expert",
     "cluster lifecycle, fleets, bootstrap, YARN, steps",
     ["sentinel.emr.analyze_ec2"]),
    ("emr-serverless-expert", "EMR Serverless Expert",
     "applications, job runs, workers, startup, capacity",
     ["sentinel.emr.analyze_serverless"]),
    ("emr-eks-expert", "EMR EKS Expert",
     "virtual clusters, namespaces, pod lifecycle, scheduling, IAM",
     ["sentinel.emr.analyze_eks"]),
    ("emr-cost-expert", "EMR Cost Expert",
     "utilization, cost drivers, capacity recommendations",
     ["sentinel.emr.estimate_cost"]),
    # §9.5 — EMR perf reuses spark-expert (no duplicated intelligence)
    ("emr-performance-expert", "EMR Performance Expert",
     "delegates to spark-expert for plans/metrics", [
         "sentinel.spark.analyze_plan", "sentinel.spark.optimize"]),
]


def specialist_descriptors() -> list[AgentDescriptor]:
    out = []
    for aid, name, resp, tools in _SPECIALISTS:
        out.append(AgentDescriptor(
            agent_id=aid, name=name, responsibility=resp,
            allowed_tools=tools))
    return out


def get_specialist(agent_id: str) -> AgentDescriptor:
    for d in specialist_descriptors():
        if d.agent_id == agent_id:
            return d
    raise KeyError(f"especialista desconhecido: {agent_id}")


# keyword → agent_id; deterministic routing, no LLM
_ROUTE: list[tuple[str, str]] = [
    ("emr serverless", "emr-serverless-expert"),
    ("serverless", "emr-serverless-expert"),
    ("emr on eks", "emr-eks-expert"), ("emr eks", "emr-eks-expert"),
    ("virtual cluster", "emr-eks-expert"),
    ("emr on ec2", "emr-ec2-expert"), ("emr cluster", "emr-ec2-expert"),
    ("emr", "emr-coordinator"),
    ("spark", "spark-expert"), ("glue", "glue-expert"),
    ("iceberg", "iceberg-expert"), ("snapshot", "iceberg-expert"),
    ("lakeformation", "lakeformation-expert"),
    ("lake formation", "lakeformation-expert"),
    ("sql", "sql-expert"), ("query", "sql-expert"),
    ("quality", "quality-expert"), ("drift", "quality-expert"),
    ("lineage", "lineage-expert"), ("iam", "security-reviewer"),
    ("policy", "security-reviewer"), ("permission", "security-reviewer"),
]


def route(problem: str) -> list[str]:
    """Deterministic keyword routing → ordered specialist ids."""
    p = problem.lower()
    ids: list[str] = []
    for kw, aid in _ROUTE:
        if kw in p and aid not in ids:
            ids.append(aid)
    return ids or ["coordinator"]


def plan_tasks(problem: str, files: dict[str, str]
               ) -> list[AgentTask]:
    """Coordinator plan: one investigate task per routed specialist."""
    tasks = []
    for i, aid in enumerate(route(problem)):
        tasks.append(AgentTask(
            task_id=f"t{i}:{aid}", agent_id=aid, kind="investigate",
            input={"problem": problem, "files": files},
            priority=i))
    tasks.append(AgentTask(
        task_id=f"t{len(tasks)}:validate",
        agent_id="evidence-validator", kind="validate",
        input={}, priority=99,
        depends_on=[t.task_id for t in tasks]))
    tasks.append(AgentTask(
        task_id=f"t{len(tasks)}:report",
        agent_id="report-specialist", kind="synthesize",
        input={}, priority=100,
        depends_on=[t.task_id for t in tasks if "validate" in t.task_id]))
    return tasks
