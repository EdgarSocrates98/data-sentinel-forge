"""Analyzer package: protocol, registry, and built-in analyzers."""

from data_sentinel.analyzers.cloudwatch import CloudWatchLogAnalyzer
from data_sentinel.analyzers.protocol import AnalysisResult, Analyzer
from data_sentinel.analyzers.registry import AnalyzerRegistry, registry
from data_sentinel.analyzers.spark import SparkGlueLogAnalyzer
from data_sentinel.analyzers.spark.config import SparkConfigAdvisor
from data_sentinel.analyzers.spark.joins import JoinIntelligenceAnalyzer
from data_sentinel.analyzers.spark.plans import SparkPlanAnalyzer
from data_sentinel.analyzers.sql import SqlStaticAnalyzer

registry.register(SparkGlueLogAnalyzer())
registry.register(SqlStaticAnalyzer())
registry.register(CloudWatchLogAnalyzer())
registry.register(SparkPlanAnalyzer())
registry.register(JoinIntelligenceAnalyzer())
registry.register(SparkConfigAdvisor())

__all__ = [
    "AnalysisResult",
    "Analyzer",
    "AnalyzerRegistry",
    "CloudWatchLogAnalyzer",
    "JoinIntelligenceAnalyzer",
    "SparkConfigAdvisor",
    "SparkGlueLogAnalyzer",
    "SparkPlanAnalyzer",
    "SqlStaticAnalyzer",
    "registry",
]
