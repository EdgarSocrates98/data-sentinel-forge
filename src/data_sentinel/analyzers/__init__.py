"""Analyzer package: protocol, registry, and built-in analyzers."""

from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.analyzers.registry import AnalyzerRegistry, registry
from data_sentinel.analyzers.spark import SparkGlueLogAnalyzer

registry.register(SparkGlueLogAnalyzer())

__all__ = [
    "AnalysisResult",
    "Analyzer",
    "AnalyzerRegistry",
    "SparkGlueLogAnalyzer",
    "registry",
]
