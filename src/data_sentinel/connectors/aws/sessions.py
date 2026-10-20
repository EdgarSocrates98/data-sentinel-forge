"""boto3 session factory — standard credential chain only.

Supports AWS profiles, environment variables, IAM roles, SSO and an optional
authorized AssumeRole. No custom credential storage, no prompting for keys.
"""

from typing import TYPE_CHECKING

from data_sentinel.connectors.aws.errors import AwsConnectorError
from data_sentinel.core.exceptions import SentinelError

if TYPE_CHECKING:  # pragma: no cover - typing only
    import boto3

DEFAULT_SESSION_NAME = "data-sentinel"


def require_boto3() -> None:
    """Fail fast with an install hint when the [aws] extra is missing."""
    try:
        import boto3  # noqa: F401
    except ImportError as exc:
        raise SentinelError(
            code="aws.boto3_ausente",
            message=(
                "conectores AWS requerem a dependência opcional boto3 — "
                "instale com: pip install 'data-sentinel[aws]'"
            ),
            details={"extra": "aws"},
        ) from exc


def build_session(
    *,
    profile: str | None = None,
    region: str | None = None,
    assume_role_arn: str | None = None,
    session_name: str = DEFAULT_SESSION_NAME,
) -> "boto3.session.Session":
    """Build a boto3 session through the standard credential chain.

    assume_role_arn performs a single sts:AssumeRole — the caller is
    responsible for having that role authorized; we never grant permissions.
    """
    require_boto3()
    import boto3

    try:
        base = boto3.session.Session(
            profile_name=profile,
            region_name=region,
        )
    except Exception as exc:  # ProfileNotFound and friends
        from data_sentinel.connectors.aws.errors import map_client_error

        raise map_client_error(exc, context="criar sessão AWS") from exc

    if assume_role_arn is None:
        return base

    try:
        creds = (
            base.client("sts")
            .assume_role(RoleArn=assume_role_arn, RoleSessionName=session_name)
            .get("Credentials", {})
        )
    except Exception as exc:
        from data_sentinel.connectors.aws.errors import map_client_error

        raise map_client_error(exc, context="assumir role AWS") from exc

    if not creds:
        raise AwsConnectorError(
            code="aws.assume_role_vazio",
            message="sts:AssumeRole retornou sem credenciais",
            details={"role_arn_present": bool(assume_role_arn)},
        )
    return boto3.session.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds.get("SessionToken"),
        region_name=region or base.region_name,
    )
