"""Spark configuration advisor."""

from data_sentinel.analyzers.spark.config.advisor import SparkConfigAdvisor
from data_sentinel.analyzers.spark.config.parser import parse_config_text

__all__ = ["SparkConfigAdvisor", "parse_config_text"]
