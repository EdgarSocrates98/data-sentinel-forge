"""Analyzer registry: registration, discovery, lookup by source type."""

from collections.abc import Iterable

from data_sentinel.analyzers.protocol import Analyzer
from data_sentinel.core.contracts import SourceType
from data_sentinel.core.exceptions import SentinelError


class AnalyzerRegistry:
    """In-memory registry of available analyzers."""

    def __init__(self) -> None:
        self._analyzers: dict[str, Analyzer] = {}

    def register(self, analyzer: Analyzer) -> None:
        if analyzer.analyzer_id in self._analyzers:
            raise SentinelError(
                code="registro.duplicado",
                message=f"analyzer duplicado: '{analyzer.analyzer_id}'",
                details={"analyzer_id": analyzer.analyzer_id},
            )
        self._analyzers[analyzer.analyzer_id] = analyzer

    def register_all(self, analyzers: Iterable[Analyzer]) -> None:
        for analyzer in analyzers:
            self.register(analyzer)

    def all(self) -> list[Analyzer]:
        return list(self._analyzers.values())

    def get(self, analyzer_id: str) -> Analyzer:
        try:
            return self._analyzers[analyzer_id]
        except KeyError as exc:
            raise SentinelError(
                code="registro.nao_encontrado",
                message=f"analyzer não encontrado: '{analyzer_id}'",
                details={"analyzer_id": analyzer_id},
            ) from exc

    def for_source_type(self, source_type: SourceType) -> list[Analyzer]:
        return [
            analyzer
            for analyzer in self._analyzers.values()
            if source_type in analyzer.supported_source_types
        ]


registry = AnalyzerRegistry()
