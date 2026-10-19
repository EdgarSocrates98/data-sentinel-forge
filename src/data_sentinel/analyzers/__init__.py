"""Analyzer package: protocol, registry, and built-in analyzers."""

from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.analyzers.registry import AnalyzerRegistry, registry
from data_sentinel.analyzers.spark import SparkGlueLogAnalyzer
from data_sentinel.analyzers.sql import SqlStaticAnalyzer

registry.register(SparkGlueLogAnalyzer())
registry.register(SqlStaticAnalyzer())

__all__ = [
    "AnalysisResult",
    "Analyzer",
    "AnalyzerRegistry",
    "SparkGlueLogAnalyzer",
    "SqlStaticAnalyzer",
    "registry",
]
