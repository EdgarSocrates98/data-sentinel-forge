"""AWS connectors — optional [aws] extra (ADR 0008/0009).

Importing this package does not import boto3; sessions.require_boto3()
fails with an install hint only when a session is actually built.
"""

from data_sentinel.connectors.aws.errors import AwsConnectorError, map_client_error
from data_sentinel.connectors.aws.glue import ALLOWED_ACTIONS, GlueConnector
from data_sentinel.connectors.aws.models import GlueJob, GlueJobRun
from data_sentinel.connectors.aws.sessions import build_session, require_boto3

__all__ = [
    "ALLOWED_ACTIONS",
    "AwsConnectorError",
    "GlueConnector",
    "GlueJob",
    "GlueJobRun",
    "build_session",
    "map_client_error",
    "require_boto3",
]
