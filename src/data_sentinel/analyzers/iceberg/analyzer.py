"""IcebergMetadataAnalyzer — §3.1-3.8.

Diagnoses table metadata supplied as input (JSON text or connector export).
Never downloads manifests/files automatically — manifest locations are read
as references, not followed. Snapshot metadata is never conflated with
observed execution metrics (§3.3): all Iceberg evidence is DECLARED.
"""

import hashlib
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from data_sentinel.analyzers.iceberg.metadata import (
    MetadataParseError,
    TableMetadata,
    parse_metadata,
)
from data_sentinel.analyzers.protocol import (
    AnalysisResult,
    Analyzer,
)
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
from data_sentinel.core.security import InputFile
from data_sentinel.core.security.sanitize import sanitize_evidence_excerpt

# Conditional small-file diagnosis: only when per-snapshot summaries carry
# both file count and byte size (§3.5 — no universal threshold).
_SMALL_FILE_AVG_BYTES = 32 * 1024 * 1024
_RETENTION_FLAG_SNAPSHOTS = 50
_SNAPSHOT_LOG_FLAG = 20


def _mb(n: float) -> str:
    return f"{n / (1024 * 1024):.1f} MB"


class IcebergMetadataAnalyzer(Analyzer):
    @property
    def analyzer_id(self) -> str:
        return "iceberg.metadata"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def supported_platforms(self) -> tuple[str, ...]:
        return (Platform.SPARK, Platform.AWS_GLUE, Platform.ATHENA)

    @property
    def supported_source_types(self) -> tuple[SourceType, ...]:
        return (SourceType.ICEBERG_METADATA,)

    @property
    def limitations(self) -> tuple[str, ...]:
        return (
        "Metadados declarados — snapshots/summaries descrevem o catálogo, "
        "não métricas de execução observadas",
        "Manifests/data files analisados somente quando fornecidos como "
        "entrada; locations são referências, nunca URLs seguidas",
        "Pruning e eficácia de partição são hipóteses sem plano/métricas",
        "Campos desconhecidos de versões mais novas são preservados, "
        "não interpretados",
        )

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=list(self.supported_platforms),
            supported_runtimes=["spark-3.3", "spark-3.5", "glue-4.0", "glue-5.0", "glue-5.1"],
            required_permissions=["filesystem:read"],
            supported_operations=["analyze_iceberg_metadata"],
            limitations=list(self.limitations),
        )

    def analyze(self, request: DiagnosticRequest, inputs: Sequence[InputFile]) -> AnalysisResult:
        started = time.monotonic()
        captured = datetime.now(UTC)
        self.validate_input(request, inputs)

        findings: list[Finding] = []
        evidence: list[Evidence] = []
        limitations: list[str] = list(self.limitations)
        tables_meta: list[dict[str, object]] = []

        for input_file in inputs:
            digest = hashlib.sha256(input_file.text.encode()).hexdigest()
            try:
                meta = parse_metadata(input_file.text, source=str(input_file.path))
            except MetadataParseError as exc:
                limitations.append(f"{input_file.path}: {exc}")
                continue

            for w in meta.warnings:
                limitations.append(f"{input_file.path}: {w}")
            if meta.extras:
                limitations.append(
                    f"{input_file.path}: campos não reconhecidos preservados "
                    f"sem interpretação: {sorted(meta.extras)}"
                )

            def _ev(
                snippet: str,
                conf: float = 0.8,
                _path: str = str(input_file.path),
                _digest: str = digest,
            ) -> Evidence:
                ev = Evidence(
                    source="iceberg_metadata",
                    source_location=_path,
                    captured_at=captured,
                    content_hash=_digest,
                    sanitized_excerpt=sanitize_evidence_excerpt(snippet, max_chars=500),
                    provenance=EvidenceProvenance.DECLARED,
                    confidence=conf,
                )
                evidence.append(ev)
                return ev

            self._snapshots(meta, _ev, findings)
            self._schemas(meta, _ev, findings)
            self._partitions(meta, _ev, findings)
            self._maintenance(meta, _ev, findings)
            tables_meta.append(
                {
                    "source": str(input_file.path),
                    "format_version": meta.format_version,
                    "schemas": len(meta.schemas),
                    "specs": len(meta.partition_specs),
                    "snapshots": len(meta.snapshots),
                    "refs": sorted(meta.refs),
                }
            )

        if not findings and not tables_meta:
            findings.append(
                Finding(
                    category=FindingCategory.UNKNOWN,
                    severity=Severity.INFO,
                    status=FindingStatus.UNKNOWN,
                    explanation=(
                        "Nenhum metadata Iceberg válido foi parseado — "
                        "verifique se a entrada é metadata.json exportado "
                        "(sem seguir URLs arbitrárias por segurança)."
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
            metadata={"tables": tables_meta},
            duration_ms=int((time.monotonic() - started) * 1000),
            analyzed_at=captured,
        )

    # -- seções ----------------------------------------------------------

    def _snapshots(
        self,
        meta: TableMetadata,
        _ev: Callable[..., Evidence],
        findings: list[Finding],
    ) -> None:
        snaps = meta.snapshots
        cur = next((s for s in snaps if s.snapshot_id == meta.current_snapshot_id), None)
        if snaps and cur is None:
            findings.append(
                Finding(
                    category=FindingCategory.DATA_QUALITY,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.CONFIRMED,
                    explanation=(
                        f"current-snapshot-id={meta.current_snapshot_id} ausente da "
                        f"lista de {len(snaps)} snapshots — metadados inconsistentes "
                        "ou coleta truncada."
                    ),
                    recommendations=[
                        "Verifique se o metadata.json é o mais recente "
                        "(compare metadata-log) e se a coleta não truncou snapshots."
                    ],
                )
            )
        if not snaps:
            return
        ops: dict[str, int] = {}
        for s in snaps:
            ops[s.operation] = ops.get(s.operation, 0) + 1
        total_added = sum(int(s.summary.get("added-data-files", 0) or 0) for s in snaps)
        total_deleted = sum(int(s.summary.get("deleted-data-files", 0) or 0) for s in snaps)
        ev = _ev(
            f"{len(snaps)} snapshots; ops={ops}; "
            f"Σ added-files={total_added} Σ deleted-files={total_deleted}; "
            f"current={meta.current_snapshot_id} (metadados declarados)"
        )
        retention = meta.properties.get("history.expire.max-snapshot-age-ms")
        if len(snaps) >= _RETENTION_FLAG_SNAPSHOTS and not retention:
            findings.append(
                Finding(
                    category=FindingCategory.COST,
                    severity=Severity.LOW,
                    status=FindingStatus.POSSIBLE,
                    explanation=(
                        f"{len(snaps)} snapshots sem política de retenção "
                        "(history.expire.max-snapshot-age-ms) declarada — "
                        "metadados crescem e planos de leitura ficam mais caros. "
                        "Hipótese sobre contagem declarada, não observada."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Avaliar expire_snapshots/retenção — decisão de "
                        "engenharia, nunca execução automática."
                    ],
                )
            )
        if cur and cur.parent_snapshot_id is not None and all(
            s.snapshot_id != cur.parent_snapshot_id for s in snaps
        ):
            _ev(
                f"snapshot atual {cur.snapshot_id} referencia parent "
                f"{cur.parent_snapshot_id} ausente — cadeia possivelmente "
                "expirada ou coleta parcial",
                conf=0.6,
            )

    def _schemas(
        self,
        meta: TableMetadata,
        _ev: Callable[..., Evidence],
        findings: list[Finding],
    ) -> None:
        if len(meta.schemas) <= 1:
            return
        names: dict[int, list[str]] = {}
        types: dict[int, list[str]] = {}
        for sc in meta.schemas:
            for fl in sc.fields:
                names.setdefault(fl.field_id, []).append(fl.name)
                types.setdefault(fl.field_id, []).append(fl.type_repr)
        renamed = [i for i, n in names.items() if len(set(n)) > 1]
        widened = [i for i, t in types.items() if len(set(t)) > 1]
        if not renamed and not widened:
            return
        ev = _ev(
            f"{len(meta.schemas)} schemas; field-ids renomeados {sorted(renamed)[:6]}; "
            f"field-ids com tipo alterado {sorted(widened)[:6]}"
        )
        findings.append(
            Finding(
                category=FindingCategory.COMPATIBILITY,
                severity=Severity.MEDIUM,
                status=FindingStatus.CONFIRMED,
                explanation=(
                    "Evolução de schema: field-ids reutilizados com nomes/tipos "
                    "distintos. Iceberg resolve por id, mas engines que leem por "
                    "posição podem falhar — compatibilidade varia por runtime."
                ),
                evidence_ids=[ev.evidence_id],
                recommendations=[
                    "Validar leitura com o runtime de destino; verificar se o "
                    "engine resolve colunas por field-id ou por posição/nome."
                ],
            )
        )

    def _partitions(
        self,
        meta: TableMetadata,
        _ev: Callable[..., Evidence],
        findings: list[Finding],
    ) -> None:
        if len(meta.partition_specs) <= 1:
            return
        ev = _ev(
            f"{len(meta.partition_specs)} partition specs "
            f"(default-spec-id={meta.default_spec_id}) — evolução de "
            "particionamento declarada"
        )
        transforms = {p.transform for s in meta.partition_specs for p in s.fields}
        if "void" in transforms:
            findings.append(
                Finding(
                    category=FindingCategory.COMPATIBILITY,
                    severity=Severity.LOW,
                    status=FindingStatus.CONFIRMED,
                    explanation=(
                        "Transform 'void' em spec mais novo desativa "
                        "particionamento de campo; partições antigas seguem "
                        "lidas pelo spec original."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Confirmar que consultas filtram pelo spec correto; "
                        "dados antigos não são reparticionados automaticamente."
                    ],
                )
            )

    def _maintenance(
        self,
        meta: TableMetadata,
        _ev: Callable[..., Evidence],
        findings: list[Finding],
    ) -> None:
        small: list[tuple[int, int, float]] = []
        for s in meta.snapshots:
            try:
                n = int(s.summary.get("added-data-files", 0) or 0)
                size = int(s.summary.get("added-files-size", 0) or 0)
            except (TypeError, ValueError):
                continue
            if n > 0 and size > 0 and size / n < _SMALL_FILE_AVG_BYTES:
                small.append((s.snapshot_id, n, size / n))
        if small:
            avg = sum(x[2] for x in small) / len(small)
            ev = _ev(
                f"{len(small)} snapshots com tamanho médio de arquivo "
                f"adicionado {_mb(avg)} (< {_mb(_SMALL_FILE_AVG_BYTES)}); "
                f"Σ arquivos={sum(x[1] for x in small)} — declarado em summary"
            )
            findings.append(
                Finding(
                    category=FindingCategory.COST,
                    severity=Severity.MEDIUM,
                    status=FindingStatus.POSSIBLE,
                    explanation=(
                        f"Indício de small files: média declarada de {_mb(avg)} "
                        "por arquivo em snapshots com métricas. Diagnóstico "
                        "condicional — depende do workload observado."
                    ),
                    evidence_ids=[ev.evidence_id],
                    recommendations=[
                        "Se leitura degrada, avaliar rewrite_data_files com "
                        "target-file-size ajustado ao engine (não automático)."
                    ],
                )
            )
        if len(meta.snapshot_log) > _SNAPSHOT_LOG_FLAG:
            findings.append(
                Finding(
                    category=FindingCategory.COST,
                    severity=Severity.LOW,
                    status=FindingStatus.CONFIRMED,
                    explanation=(
                        f"{len(meta.snapshot_log)} entradas de snapshot-log — "
                        "listagens de catálogo ficam mais caras."
                    ),
                    recommendations=[
                        "Revisar retenção (history.expire.*) conforme SLA."
                    ],
                )
            )
