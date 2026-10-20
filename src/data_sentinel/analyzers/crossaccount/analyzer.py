"""Cross-account diagnostics analyzer — §5, ds-0024.

Consumes AccessContext JSON (source_type=ACCESS_CONTEXT): accounts, region,
catalog, database, table, resource link, LF mode, observed/unknown
permissions. Builds the logical permissions graph and emits findings for
cross-account read/write scenarios. Lack of visibility = unknown,
never denial (§5.2).
"""

import hashlib
import json
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from data_sentinel.analyzers.crossaccount.graph import (
    EdgeProvenance,
    EdgeType,
    PermissionsGraph,
)
from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.core.contracts.entities import (
    CapabilityManifest,
    DiagnosticRequest,
    Evidence,
    Finding,
)
from data_sentinel.core.contracts.enums import (
    EvidenceProvenance,
    FindingCategory,
    FindingStatus,
    Platform,
    Severity,
    SourceType,
)
from data_sentinel.core.contracts.lakehouse import AccessContext
from data_sentinel.core.security import InputFile
from data_sentinel.core.security.sanitize import sanitize_evidence_excerpt

_EvFn = Callable[..., Evidence]


def _prov(v: str) -> EdgeProvenance:
    return {
        "observed": EdgeProvenance.OBSERVED,
        "declared": EdgeProvenance.DECLARED,
        "inferred": EdgeProvenance.INFERRED,
    }.get(v, EdgeProvenance.UNVERIFIED)


class CrossAccountAnalyzer(Analyzer):
    @property
    def analyzer_id(self) -> str:
        return "lakehouse.cross_account"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def supported_platforms(self) -> tuple[str, ...]:
        return (Platform.AWS_GLUE, Platform.ATHENA)

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (SourceType.ACCESS_CONTEXT,)

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
            "Contexto de acesso é declarado/fornecido — permissões não "
            "visíveis são UNKNOWN, nunca presumidas negadas",
            "Grants Lake Formation analisados apenas quando fornecidos "
            "no contexto; sem chamada mutadora",
            "Compatibilidade de cenário cross-account depende de regras "
            "de conhecimento — ausência de regra → UNKNOWN",
        )

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=list(self.supported_platforms),
            supported_runtimes=["glue-4.0", "glue-5.0", "glue-5.1"],
            required_permissions=["filesystem:read"],
            supported_operations=["analyze_cross_account"],
            limitations=list(self.limitations),
        )

    def analyze(self, request: DiagnosticRequest, inputs: Sequence[InputFile]) -> AnalysisResult:
        started = time.monotonic()
        captured = datetime.now(UTC)
        self.validate_input(request, inputs)

        findings: list[Finding] = []
        evidence: list[Evidence] = []
        limitations: list[str] = list(self.limitations)
        graphs_meta: list[dict[str, object]] = []

        for input_file in inputs:
            digest = hashlib.sha256(input_file.text.encode()).hexdigest()
            ctx, err = self._load_ctx(input_file)
            if err or ctx is None:
                limitations.append(f"{input_file.path}: {err}")
                continue

            def _ev(snippet: str, conf: float = 0.75,
                    _path: str = str(input_file.path),
                    _digest: str = digest) -> Evidence:
                ev = Evidence(
                    source="access_context",
                    source_location=_path,
                    captured_at=captured,
                    content_hash=_digest,
                    sanitized_excerpt=sanitize_evidence_excerpt(snippet, max_chars=500),
                    provenance=EvidenceProvenance.DECLARED,
                    confidence=conf,
                )
                evidence.append(ev)
                return ev

            graph = self._build_graph(ctx)
            graphs_meta.append({"source": str(input_file.path), **self._counts(graph)})

            self._resource_link(ctx, _ev, findings, limitations)
            self._lf_permissions(ctx, _ev, findings, limitations)
            self._cross_account(ctx, graph, _ev, findings, limitations)
            if graph.unverified():
                limitations.append(
                    f"{input_file.path}: {len(graph.unverified())} arestas do "
                    "grafo marcadas unverified — visibilidade incompleta, "
                    "não negação"
                )

        if not findings:
            findings.append(
                Finding(
                    category=FindingCategory.UNKNOWN,
                    severity=Severity.INFO,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        "Nenhum diagnóstico cross-account confirmado — "
                        "contexto insuficiente não gera causa-raiz fabricada."
                    ),
                    evidence_ids=[],
                )
            )

        return AnalysisResult(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.version,
            request_id=request.request_id,
            findings=findings,
            evidence=evidence,
            limitations=limitations,
            metadata={"graphs": graphs_meta},
            duration_ms=int((time.monotonic() - started) * 1000),
            analyzed_at=captured,
        )

    # ------------------------------------------------------------------

    def _load_ctx(self, f: InputFile) -> tuple[AccessContext | None, str | None]:
        try:
            raw = json.loads(f.text)
        except json.JSONDecodeError as exc:
            return None, f"contexto de acesso não é JSON: {exc}"
        if not isinstance(raw, dict):
            return None, "contexto de acesso deve ser objeto JSON"
        try:
            return AccessContext.model_validate(raw), None
        except Exception as exc:  # pydantic validation → limitation, never crash
            return None, f"contexto inválido: {exc}"

    def _build_graph(self, ctx: AccessContext) -> PermissionsGraph:
        g = PermissionsGraph()
        src_acct = f"account:{ctx.source_account}" if ctx.source_account else ""
        dst_acct = f"account:{ctx.destination_account}" if ctx.destination_account else ""
        principal = f"principal:{ctx.principal}" if ctx.principal else ""
        catalog = f"catalog:{ctx.catalog}@{ctx.region}" if ctx.catalog else ""
        table = f"table:{ctx.database}.{ctx.table}" if ctx.database and ctx.table else ""
        link = f"resource_link:{ctx.resource_link}" if ctx.resource_link else ""

        for nid, kind in [
            (src_acct, "account"), (dst_acct, "account"),
            (principal, "principal"), (catalog, "catalog"),
            (table, "table"), (link, "resource_link"),
        ]:
            if nid:
                g.add_node(nid, kind)

        if principal and src_acct:
            g.add_edge(principal, src_acct, EdgeType.ASSUMES_ROLE,
                       EdgeProvenance.DECLARED, "principal declarado na conta origem")
        if link and table:
            g.add_edge(link, table, EdgeType.REFERENCES,
                       EdgeProvenance.DECLARED, "resource link aponta para tabela alvo")
        if link and catalog:
            g.add_edge(link, catalog, EdgeType.REFERENCES,
                       EdgeProvenance.INFERRED, "link resolve via catálogo de destino")
        if src_acct and dst_acct and src_acct != dst_acct:
            g.add_edge(dst_acct, src_acct, EdgeType.SHARES_WITH,
                       EdgeProvenance.UNVERIFIED,
                       "compartilhamento cross-account não confirmado — "
                       "grants LF não visíveis")
        for perm in ctx.observed_permissions:
            if principal and table:
                g.add_edge(principal, table, EdgeType.GRANTED_ON,
                           EdgeProvenance.OBSERVED, f"permissão observada: {perm}")
        for perm in ctx.unknown_permissions:
            if principal and table:
                g.add_edge(principal, table, EdgeType.GRANTED_ON,
                           EdgeProvenance.UNVERIFIED, f"permissão não visível: {perm}")
        return g

    @staticmethod
    def _counts(g: PermissionsGraph) -> dict[str, object]:
        return {
            "nodes": len(g.nodes),
            "edges": len(g.edges),
            "unverified_edges": len(g.unverified()),
            "graph": g.to_dict(),
        }

    def _resource_link(
        self,
        ctx: AccessContext,
        _ev: _EvFn,
        findings: list[Finding],
        limitations: list[str],
    ) -> None:
        if not ctx.resource_link:
            limitations.append(
                "Sem resource link declarado — cenário de compartilhamento "
                "via link não avaliável (não é evidência de falta)."
            )
            return
        _ev(f"resource link '{ctx.resource_link}' → "
            f"{ctx.database}.{ctx.table} na região {ctx.region or 'desconhecida'}")
        if not ctx.region:
            findings.append(
                Finding(
                    category=FindingCategory.COMPATIBILITY,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        f"Resource link '{ctx.resource_link}' sem região "
                        "declarada — resolução cross-region não verificável."
                    ),
                    recommendations=[
                        "Declare a região do catálogo de destino ou exporte "
                        "GetTable do catálogo para confirmar o alvo."
                    ],
                )
            )

    def _lf_permissions(
        self,
        ctx: AccessContext,
        _ev: _EvFn,
        findings: list[Finding],
        limitations: list[str],
    ) -> None:
        if ctx.lf_mode == "unknown":
            limitations.append(
                "Modo Lake Formation não identificado — FGAC/FTA não "
                "presumidos; grants visíveis são analisados, ausência "
                "de grant visível NÃO é negação."
            )
        if ctx.unknown_permissions:
            ev = _ev(
                f"{len(ctx.unknown_permissions)} permissões sem visibilidade: "
                f"{ctx.unknown_permissions[:6]} — tratadas como unknown",
                conf=0.5,
            )
            findings.append(
                Finding(
                    category=FindingCategory.PERMISSIONS,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        "Permissões Lake Formation parcialmente invisíveis — "
                        "o contexto não expõe grants suficientes para afirmar "
                        "autorização nem negação."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Exportar ListPermissions/GetTableObjects do catálogo "
                        "de destino com credencial autorizada para elevar "
                        "a confiança do diagnóstico."
                    ],
                )
            )

    def _cross_account(
        self,
        ctx: AccessContext,
        graph: PermissionsGraph,
        _ev: _EvFn,
        findings: list[Finding],
        limitations: list[str],
    ) -> None:
        if not ctx.source_account or not ctx.destination_account:
            return
        same = ctx.source_account == ctx.destination_account
        op = (ctx.required_operation or "").lower()
        if same:
            limitations.append(
                "Contas origem/destino iguais — diagnóstico cross-account "
                "revertido para análise single-account."
            )
            return
        ev = _ev(
            f"cross-account {ctx.source_account} → {ctx.destination_account}; "
            f"op={op or 'não declarada'}; lf_mode={ctx.lf_mode}; "
            f"observadas={len(ctx.observed_permissions)} "
            f"desconhecidas={len(ctx.unknown_permissions)}"
        )
        read_like = op in ("select", "describe", "metadata", "read", "")
        write_like = op in ("insert", "append", "update", "delete", "merge",
                            "create", "alter", "drop", "write")
        if read_like and not ctx.observed_permissions and ctx.unknown_permissions:
            findings.append(
                Finding(
                    category=FindingCategory.PERMISSIONS,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        f"Leitura cross-account {ctx.source_account}→"
                        f"{ctx.destination_account} sem grants observados — "
                        "não é possível afirmar autorização nem negação."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Verificar grant LF cross-account na conta de destino "
                        "e o data access do resource link na conta de origem."
                    ],
                )
            )
        if write_like:
            findings.append(
                Finding(
                    category=FindingCategory.COMPATIBILITY,
                    severity=Severity.HIGH,
                    status=FindingStatus.POSSIBLE,
                    explanation=(
                        f"Escrita cross-account '{op}' exige cadeia completa: "
                        "leitura na origem + grant de escrita no destino + "
                        "catálogos alinhados + S3/KMS das DUAS contas. "
                        "Cada elo não verificado mantém o veredito POSSIBLE."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Validar separadamente: (1) leitura origem, "
                        "(2) escrita destino, (3) catálogos, (4) S3, (5) KMS — "
                        "falha em qualquer elo explica o AccessDenied."
                    ],
                )
            )
