"""Analyzer protocol: the stable interface every analyzer implements (§01.3)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from data_sentinel.core.contracts import (
    CapabilityManifest,
    DiagnosticRequest,
    Evidence,
    Finding,
    SourceType,
)
from data_sentinel.core.exceptions import InputValidationError
from data_sentinel.core.security import InputFile


@dataclass(frozen=True)
class AnalysisResult:
    """Internal output of one analyzer pass over one request.

    Not a wire contract — the report builder (ds-0007/CLI) maps this onto
    a DiagnosticReport.
    """

    analyzer_id: str
    analyzer_version: str
    request_id: str
    findings: list[Finding]
    evidence: list[Evidence]
    limitations: list[str]
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class Analyzer(ABC):
    """Deterministic, local, read-only analyzer contract."""

    @property
    @abstractmethod
    def analyzer_id(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @property
    @abstractmethod
    def supported_source_types(self) -> tuple[SourceType, ...]: ...

    @property
    @abstractmethod
    def supported_platforms(self) -> tuple[str, ...]: ...

    @property
    @abstractmethod
    def limitations(self) -> tuple[str, ...]: ...

    def validate_input(self, request: DiagnosticRequest, inputs: Sequence[InputFile]) -> None:
        """Reject requests the analyzer cannot serve. Pure validation, no IO."""
        if request.source_type not in self.supported_source_types:
            raise InputValidationError(
                code="analisador.fonte_nao_suportada",
                message=(
                    f"analyzer '{self.analyzer_id}' não suporta source_type "
                    f"'{request.source_type}'; suportados: "
                    f"{[s.value for s in self.supported_source_types]}"
                ),
                details={
                    "analyzer": self.analyzer_id,
                    "source_type": request.source_type.value,
                },
            )
        if not inputs:
            raise InputValidationError(
                code="analisador.sem_entradas",
                message=f"analyzer '{self.analyzer_id}' recebeu nenhum artefato de entrada",
                details={"analyzer": self.analyzer_id},
            )

    @abstractmethod
    def analyze(self, request: DiagnosticRequest, inputs: Sequence[InputFile]) -> AnalysisResult:
        """Run the deterministic pass. Never fabricates findings."""
        ...

    def capabilities(self) -> CapabilityManifest:
        from data_sentinel.core.contracts import Platform

        return CapabilityManifest(
            capability_id=self.analyzer_id,
            version=self.version,
            supported_platforms=[Platform(p) for p in self.supported_platforms],
            supported_runtimes=[],
            required_permissions=["filesystem:read"],
            supported_operations=[s.value for s in self.supported_source_types],
            limitations=list(self.limitations),
        )
