"""Static SQL analyzer via SQLGlot — Spark SQL + Trino/Presto (Athena).

Static analysis only: never executes, never infers physical plans (§02.5).
Status taxonomy: CONFIRMED only for syntactically certain antipattern
presence (cross/implicit join), POSSIBLE for heuristic hints.
"""

import hashlib
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import sqlglot
from sqlglot import exp

from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.analyzers.spark.joins.extractor import load_stats
from data_sentinel.core.contracts import (
    DiagnosticRequest,
    Evidence,
    EvidenceProvenance,
    Finding,
    FindingCategory,
    FindingStatus,
    Platform,
    Severity,
    SourceType,
)
from data_sentinel.core.security import InputFile, sanitize_evidence_excerpt

PLATFORM_DIALECTS: dict[Platform, str] = {
    Platform.SPARK: "spark",
    Platform.AWS_GLUE: "spark",
    Platform.DATABRICKS: "spark",
    Platform.TRINO: "trino",
    Platform.ATHENA: "trino",
    Platform.ICEBERG: "spark",
    Platform.GENERIC: "spark",
}

IN_LIST_THRESHOLD = 20

SEMANTIC_CHECKLIST = (
    "Checklist antes de aplicar qualquer sugestão: validar schema, tipos, "
    "semântica de NULL, duplicatas, cardinalidade, ordenação quando "
    "relevante, regras de negócio e equivalência de resultados — "
    "equivalência NÃO é garantida por comparação de AST."
)


SqlHit = exp.Expr | str


@dataclass(frozen=True)
class SqlCheck:
    check_id: str
    severity: Severity
    status: FindingStatus
    title: str
    rationale: str
    suggestion: str
    detect: Callable[[exp.Expr, str], list[SqlHit]]


def _select_stars(tree: exp.Expr, _text: str) -> list[SqlHit]:
    """Bare SELECT * hits. Stars inside EXISTS/COUNT wrappers are
    legitimate — the count/existence test reads no columns."""
    hits: list[SqlHit] = []
    for star in tree.find_all(exp.Star):
        parent = star.parent
        inside_wrapper = False
        while parent is not None:
            if isinstance(parent, (exp.Exists, exp.Count, exp.AggFunc)):
                inside_wrapper = True
                break
            parent = parent.parent
        if not inside_wrapper:
            hits.append(star)
    return hits


def _is_trivial_on(on: exp.Expr | None) -> bool:
    """True when ON is absent or a constant TRUE (sqlglot synthesizes on=TRUE
    for JOIN without predicate)."""
    if on is None:
        return True
    return isinstance(on, exp.Boolean) and on.this is True


def _predicateless_joins(tree: exp.Expr, _text: str) -> list[SqlHit]:
    hits: list[SqlHit] = []
    for join in tree.find_all(exp.Join):
        kind = str(join.args.get("kind") or "").upper()
        cross = kind == "CROSS"
        if cross or (not join.args.get("using") and _is_trivial_on(join.args.get("on"))):
            hits.append(join)
    return hits


_COMMA_FROM_RE = re.compile(
    r"\bFROM\s+[^\s,()]+\s+(?:AS\s+)?[A-Za-z_]\w*\s*,", re.IGNORECASE
)


def _implicit_joins(tree: exp.Expr, text: str) -> list[SqlHit]:
    """Comma-syntax joins: sqlglot normalizes them to CROSS joins, so the
    textual `FROM a, b` shape is detected on the raw text."""
    _ = tree
    return [m.group(0) for m in _COMMA_FROM_RE.finditer(text)]


def _nonsargable_predicates(tree: exp.Expr, _text: str) -> list[SqlHit]:
    hits: list[SqlHit] = []
    for where in tree.find_all(exp.Where):
        for func in where.find_all(exp.Func):
            if func.find(exp.Column) is not None:
                hits.append(func)
    return hits


def _order_without_limit(tree: exp.Expr, _text: str) -> list[SqlHit]:
    hits: list[SqlHit] = []
    for select in tree.find_all(exp.Select):
        if select.args.get("order") and not select.args.get("limit"):
            hits.append(select.args["order"])
    return hits


def _union_without_all(tree: exp.Expr, _text: str) -> list[SqlHit]:
    return [u for u in tree.find_all(exp.Union) if u.args.get("distinct", True)]


def _count_distinct(tree: exp.Expr, _text: str) -> list[SqlHit]:
    return [c for c in tree.find_all(exp.Count) if c.args.get("distinct")]


def _large_in_lists(tree: exp.Expr, _text: str) -> list[SqlHit]:
    return [
        i
        for i in tree.find_all(exp.In)
        if len(i.args.get("expressions") or []) >= IN_LIST_THRESHOLD
    ]


def _cast_on_join_key(tree: exp.Expr, _text: str) -> list[SqlHit]:
    hits: list[SqlHit] = []
    for join in tree.find_all(exp.Join):
        on = join.args.get("on")
        if on is None:
            continue
        for cast in on.find_all(exp.Cast):
            if cast.find(exp.Column) is not None:
                hits.append(cast)
    return hits


def _func_on_join_key(tree: exp.Expr, _text: str) -> list[SqlHit]:
    hits: list[SqlHit] = []
    for join in tree.find_all(exp.Join):
        on = join.args.get("on")
        if on is None:
            continue
        for func in on.find_all(exp.Func):
            if not isinstance(func, exp.Cast) and func.find(exp.Column) is not None:
                hits.append(func)
    return hits


def _complex_subqueries(tree: exp.Expr, _text: str) -> list[SqlHit]:
    hits: list[SqlHit] = []
    for sub in tree.find_all(exp.Subquery):
        depth = sum(1 for _ in list(sub.find_all(exp.Subquery)))
        if depth >= 2:
            hits.append(sub)
    return hits


def _select_distinct(tree: exp.Expr, _text: str) -> list[SqlHit]:
    return [
        s.args["distinct"]
        for s in tree.find_all(exp.Select)
        if s.args.get("distinct")
    ]


def _unfiltered_scan(tree: exp.Expr, _text: str) -> list[SqlHit]:
    """SELECT over a table with no WHERE/LIMIT anywhere in that SELECT's
    scope — a broad read. Contextual: may be intentional (full dumps)."""
    hits: list[SqlHit] = []
    for select in tree.find_all(exp.Select):
        if (
            select.args.get("from_") is not None
            and select.args.get("where") is None
            and select.args.get("limit") is None
            and select.find(exp.Join) is None
        ):
            hits.append(select.args["from_"])
    return hits


def _reused_join_keys(tree: exp.Expr, _text: str) -> list[SqlHit]:
    """Same key column name reused across multiple joins — potential
    multiplicative fan-out when intermediate joins are many-to-many."""
    from collections import Counter

    key_names: Counter[str] = Counter()
    join_nodes: dict[str, exp.Expr] = {}
    for join in tree.find_all(exp.Join):
        on = join.args.get("on")
        if on is None:
            continue
        for col in on.find_all(exp.Column):
            key_names[col.name] += 1
            join_nodes.setdefault(col.name, join)
    return [
        join_nodes[name]
        for name, count in key_names.items()
        if count >= 3  # key appears on both sides of >=2 joins → count>=3 cols
    ]


SQL_CHECKS: tuple[SqlCheck, ...] = (
    SqlCheck(
        "select-star",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "SELECT * / projeção ampla",
        "Projetar todas as colunas lê dados desnecessários e dificulta "
        "predicate/projection pushdown.",
        "Listar explicitamente as colunas necessárias.",
        _select_stars,
    ),
    SqlCheck(
        "join-without-predicate",
        Severity.HIGH,
        FindingStatus.CONFIRMED,
        "JOIN sem predicado (produto cartesiano)",
        "JOIN sem ON/USING ou CROSS JOIN gera produto cartesiano — "
        "presença sintaticamente certa; o impacto depende do plano.",
        "Adicionar predicado de junção ou confirmar intenção de CROSS JOIN.",
        _predicateless_joins,
    ),
    SqlCheck(
        "implicit-comma-join",
        Severity.MEDIUM,
        FindingStatus.POSSIBLE,
        "Join implícito com vírgula",
        "Sintaxe `FROM a, b` esconde a condição de junção e favorece "
        "produto cartesiano acidental.",
        "Reescrever com JOIN ... ON explícito.",
        _implicit_joins,
    ),
    SqlCheck(
        "non-sargable-predicate",
        Severity.MEDIUM,
        FindingStatus.POSSIBLE,
        "Predicado não-sargable (função envolvendo coluna)",
        "Função sobre coluna em WHERE impede uso de estatísticas/partição "
        "pelo otimizador.",
        "Mover a função para o lado literal ou materializar a coluna.",
        _nonsargable_predicates,
    ),
    SqlCheck(
        "order-by-without-limit",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "ORDER BY sem LIMIT",
        "Ordenação global completa é cara e raramente necessária sem limite.",
        "Avaliar LIMIT ou ordenar somente no consumidor.",
        _order_without_limit,
    ),
    SqlCheck(
        "union-without-all",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "UNION sem ALL",
        "UNION sem ALL executa deduplicação custosa; frequentemente o "
        "intencionado é UNION ALL.",
        "Confirmar necessidade de deduplicar ou usar UNION ALL.",
        _union_without_all,
    ),
    SqlCheck(
        "count-distinct",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "COUNT(DISTINCT)",
        "COUNT(DISTINCT) concentra dados em poucos reducers; em volumes "
        "grandes merece aproximação ou reescrita.",
        "Avaliar approx_count_distinct ou agregação em duas fases.",
        _count_distinct,
    ),
    SqlCheck(
        "large-in-list",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "Lista IN literal grande",
        f"IN (...) com ≥{IN_LIST_THRESHOLD} literais pode indicar filtro "
        "que deveria ser join com tabela de dimensão.",
        "Materializar valores em tabela e usar JOIN/semi-join.",
        _large_in_lists,
    ),
    SqlCheck(
        "cast-on-join-key",
        Severity.MEDIUM,
        FindingStatus.POSSIBLE,
        "CAST em chave de JOIN",
        "CAST sobre coluna na condição de junção derrota "
        "bucketing/partitioning e pode indicar tipos inconsistentes "
        "entre tabelas.",
        "Alinhar tipos no schema ou materializar a coluna convertida — "
        "validar semântica de NULL e precisão antes de mudar.",
        _cast_on_join_key,
    ),
    SqlCheck(
        "function-on-join-key",
        Severity.MEDIUM,
        FindingStatus.POSSIBLE,
        "Função sobre chave de JOIN",
        "Função envolvendo coluna na condição de junção pode impedir "
        "partition pruning e o uso de índices/estatísticas.",
        "Reescrever a expressão sobre a chave ou materializar a coluna "
        "derivada — validar equivalência de resultados.",
        _func_on_join_key,
    ),
    SqlCheck(
        "complex-subquery",
        Severity.MEDIUM,
        FindingStatus.POSSIBLE,
        "Subqueries aninhadas profundas",
        "Aninhamento ≥2 níveis aumenta custo de otimização e risco de "
        "recomputação; CTEs nomeadas são mais auditáveis.",
        "Avaliar extração para CTE — semântica de duplicatas/NULLs "
        "pode mudar; validar equivalência.",
        _complex_subqueries,
    ),
    SqlCheck(
        "select-distinct",
        Severity.MEDIUM,
        FindingStatus.POSSIBLE,
        "SELECT DISTINCT potencialmente custoso",
        "DISTINCT global força deduplicação completa; em joins com "
        "fan-out pode mascarar multiplicidade errada.",
        "Verificar se a duplicata vem de join many-to-many; considerar "
        "GROUP BY nas chaves reais.",
        _select_distinct,
    ),
    SqlCheck(
        "unfiltered-scan",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "Leitura ampla sem WHERE/LIMIT",
        "SELECT sobre tabela sem filtro nem limite lê a relação "
        "inteira — pode ser intencional (carga completa) ou filtro "
        "esquecido.",
        "Confirmar intenção; se for exploração, adicionar LIMIT.",
        _unfiltered_scan,
    ),
    SqlCheck(
        "reused-join-key",
        Severity.LOW,
        FindingStatus.POSSIBLE,
        "Chave de join reutilizada em múltiplos joins",
        "Mesma coluna em ≥2 predicados de join pode indicar fan-out "
        "multiplicativo quando joins intermediários são many-to-many.",
        "Medir multiplicidade por chave nos lados antes de assumir "
        "cardinalidade.",
        _reused_join_keys,
    ),
)


def _dialect_for(request: DiagnosticRequest) -> str:
    extra = (request.execution_context.extra if request.execution_context else {})
    return extra.get("sql_dialect") or PLATFORM_DIALECTS.get(request.platform, "spark")


def _line_of_fragment(source: str, fragment: str) -> int:
    needle = fragment.split("\n", 1)[0][:60]
    if not needle:
        return 1
    idx = source.find(needle)
    if idx < 0:
        return 1
    return source[:idx].count("\n") + 1


def _query_structure(tree: exp.Expr, dialect: str) -> dict[str, object]:
    """Structured representation from the AST — join graph, tables vs
    CTEs, predicates, aggregations, subquery depth, costly ops."""
    cte_names = {c.alias for c in tree.find_all(exp.CTE)}
    tables = []
    for t in tree.find_all(exp.Table):
        tables.append(
            {
                "name": t.name,
                "alias": t.alias or None,
                "is_cte": t.name in cte_names,
            }
        )
    join_graph = []
    for j in tree.find_all(exp.Join):
        on = j.args.get("on")
        join_graph.append(
            {
                "kind": str(j.args.get("kind") or "INNER").upper(),
                "side": str(j.args.get("side") or "").upper() or None,
                "table": getattr(j.this, "name", None)
                or getattr(j.this, "alias_or_name", None),
                "predicate": on.sql(dialect=dialect)[:200] if on is not None else None,
                "equality_keys": [
                    f"{eq.left.sql(dialect=dialect)}={eq.right.sql(dialect=dialect)}"
                    for eq in (on.find_all(exp.EQ) if on is not None else [])
                ][:8],
            }
        )
    predicates = [
        w.sql(dialect=dialect)[:200] for w in tree.find_all(exp.Where)
    ]
    aggregations = sorted(
        {a.sql(dialect=dialect)[:60] for a in tree.find_all(exp.AggFunc)}
    )
    max_depth = 0
    for sub in tree.find_all(exp.Subquery):
        depth = 1
        node: exp.Expr = sub
        while node.parent is not None:
            if isinstance(node.parent, exp.Subquery):
                depth += 1
            node = node.parent
        max_depth = max(max_depth, depth)
    costly = []
    for check in SQL_CHECKS:
        if check.detect(tree, ""):
            costly.append(check.check_id)
    return {
        "tables": tables,
        "join_graph": join_graph,
        "predicates": predicates,
        "aggregations": aggregations,
        "cte_count": len(cte_names),
        "subquery_max_depth": max_depth,
        "window_functions": len(list(tree.find_all(exp.Window))),
        "costly_operation_candidates": costly,
    }


class SqlStaticAnalyzer(Analyzer):
    """Pattern-based static inspection of SQL text. No execution, no plan."""

    @property
    def analyzer_id(self) -> str:
        return "sql-static-analyzer"

    @property
    def version(self) -> str:
        return "0.2.0"

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (SourceType.SQL_QUERY,)

    @property
    def supported_platforms(self) -> tuple[str, ...]:
        return ("spark", "aws_glue", "trino", "athena", "generic")

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
            "Análise estática: não observa execução física nem custos reais",
            "Sem acesso a catálogo: não valida existência de tabelas/colunas",
            "Cobertura limitada à lista de antipadrões documentada",
        )

    def _check_selectivity(
        self,
        tree: exp.Expr,
        input_file: InputFile,
        digest: str,
        captured: datetime,
        stats: dict[str, object],
        findings: list[Finding],
        evidence: list[Evidence],
    ) -> None:
        """Flag WHERE equality predicates on columns whose declared
        top-key concentration suggests low selectivity."""
        for where in tree.find_all(exp.Where):
            for eq in where.find_all(exp.EQ):
                cols = list(eq.find_all(exp.Column))
                if len(cols) != 1:
                    continue
                for tname, meta in stats.items():
                    top = getattr(meta, "top_keys", None) or []
                    for tk in top:
                        frac = float(tk.get("fraction", 0) or 0)
                        if frac >= 0.5:
                            ev = Evidence(
                                source="sql",
                                source_location=str(input_file.path),
                                captured_at=captured,
                                content_hash=digest,
                                sanitized_excerpt=sanitize_evidence_excerpt(
                                    eq.sql()[:300], max_chars=400
                                ),
                                provenance=EvidenceProvenance.DECLARED,
                                confidence=0.6,
                            )
                            evidence.append(ev)
                            findings.append(
                                Finding(
                                    category=FindingCategory.COST,
                                    severity=Severity.LOW,
                                    status=FindingStatus.POSSIBLE,
                                    explanation=(
                                        f"Predicado potencialmente pouco "
                                        f"seletivo: '{tk.get('key', '?')}' "
                                        f"cobre {frac:.0%} das linhas "
                                        f"declaradas de {tname}. "
                                        "Avaliar se o filtro reduz o volume "
                                        "esperado."
                                    ),
                                    evidence_ids=[ev.evidence_id],
                                    recommendations=[
                                        "Medir selectividade real com "
                                        "amostra antes de assumir pruning",
                                        SEMANTIC_CHECKLIST,
                                    ],
                                )
                            )
                            return

    def analyze(self, request: DiagnosticRequest, inputs: Sequence[InputFile]) -> AnalysisResult:
        self.validate_input(request, inputs)
        captured = datetime.now(UTC)
        dialect = _dialect_for(request)

        findings: list[Finding] = []
        evidence: list[Evidence] = []
        limitations: list[str] = [
            "Análise estática: não observa execução física (plano, métricas, "
            "estatísticas).",
        ]
        queries_meta: list[dict[str, object]] = []
        stats_meta: dict[str, object] = {}
        declared_stats: dict[str, object] = {}

        sql_inputs: list[InputFile] = []
        for input_file in inputs:
            if str(input_file.path).endswith(".json"):
                tables, _runtime, warns = load_stats(input_file.text)
                declared_stats.update(tables)
                stats_meta = {
                    "tables_with_stats": sorted(tables),
                    "source": "declared (descritor JSON)",
                }
                limitations.extend(
                    f"{input_file.path}: {w}" for w in warns
                )
            else:
                sql_inputs.append(input_file)

        for input_file in sql_inputs:
            digest = hashlib.sha256(input_file.text.encode()).hexdigest()
            try:
                tree = sqlglot.parse_one(input_file.text, read=dialect)
            except sqlglot.errors.ParseError as exc:
                limitations.append(
                    f"SQL não pôde ser analisado ({input_file.path}): {exc}"
                )
                findings.append(
                    Finding(
                        category=FindingCategory.UNKNOWN,
                        severity=Severity.INFO,
                        status=FindingStatus.UNKNOWN,
                        explanation=(
                            "Entrada SQL inválida para o dialeto "
                            f"'{dialect}': {exc}. Nenhuma análise de padrões "
                            "foi aplicada."
                        ),
                    )
                )
                continue

            if tree is None:
                limitations.append(f"SQL vazio ou sem statement: {input_file.path}")
                continue

            queries_meta.append(
                {
                    "file": str(input_file.path),
                    **_query_structure(tree, dialect),
                }
            )

            if declared_stats:
                self._check_selectivity(
                    tree, input_file, digest, captured, declared_stats,
                    findings, evidence,
                )
            for check in SQL_CHECKS:
                hits = check.detect(tree, input_file.text)
                if not hits:
                    continue
                ids: list[str] = []
                for hit in hits[:3]:
                    fragment = (
                        hit[:300]
                        if isinstance(hit, str)
                        else hit.sql(dialect=dialect)[:300]
                    )
                    ev = Evidence(
                        source="sql",
                        source_location=(
                            f"{input_file.path}:{_line_of_fragment(input_file.text, fragment)}"
                        ),
                        captured_at=captured,
                        content_hash=digest,
                        sanitized_excerpt=sanitize_evidence_excerpt(fragment, max_chars=400),
                        provenance=EvidenceProvenance.STATIC_INFERRED,
                        confidence=0.9 if check.status == FindingStatus.CONFIRMED else 0.55,
                    )
                    evidence.append(ev)
                    ids.append(ev.evidence_id)
                findings.append(
                    Finding(
                        category=FindingCategory.SQL_ANTIPATTERN,
                        severity=check.severity,
                        status=check.status,
                        explanation=(
                            f"{check.title}: {check.rationale} "
                            f"({len(hits)} ocorrência(s), dialeto {dialect})."
                        ),
                        evidence_ids=ids,
                        alternatives=[],
                        recommendations=[check.suggestion, SEMANTIC_CHECKLIST],
                        validation_steps=[
                            "Revisar a ocorrência indicada na evidência",
                            "Confirmar intenção antes de reescrever",
                        ],
                    )
                )

        engine = (
            "athena/trino" if dialect == "trino" else "spark"
        )
        if dialect == "trino":
            limitations.append(
                "Engine assumido: Athena/Trino — conector-based, sem AQE/"
                "bucketing Spark; estratégias físicas e pruning diferem do "
                "Spark. Nenhuma afirmação sobre execução Spark se aplica."
            )
        else:
            limitations.append(
                "Engine assumido: Spark — estratégias (AQE, broadcast, "
                "shuffle) não se aplicam a execução Athena/Trino."
            )
        return AnalysisResult(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.version,
            request_id=request.request_id,
            findings=findings,
            evidence=evidence,
            limitations=limitations,
            metadata={
                "dialect": dialect,
                "engine": engine,
                "queries": queries_meta,
                "statistics": stats_meta,
            },
        )
