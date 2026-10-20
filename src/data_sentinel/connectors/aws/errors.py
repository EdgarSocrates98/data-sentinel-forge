"""AWS error taxonomy → structured SentinelError.

Shared by all AWS connectors (Glue, CloudWatch). Maps botocore ClientError
codes to stable domain codes with PT-BR next-step hints. Never exposes
credential material.
"""

from typing import Any

from data_sentinel.core.exceptions import SentinelError


class AwsConnectorError(SentinelError):
    """Error raised by AWS connectors with a stable taxonomy code."""


_ERROR_MAP: dict[str, tuple[str, str]] = {
    "AccessDeniedException": (
        "aws.acesso_negado",
        "permissão negada — revise a política IAM mínima em docs/guides/",
    ),
    "AccessDenied": (
        "aws.acesso_negado",
        "permissão negada — revise a política IAM mínima em docs/guides/",
    ),
    "EntityNotFoundException": (
        "aws.nao_encontrado",
        "recurso não encontrado — confira nome, região e se o recurso ainda existe",
    ),
    "ResourceNotFoundException": (
        "aws.nao_encontrado",
        "recurso não encontrado — confira nome, região e se o recurso ainda existe",
    ),
    "InvalidInputException": (
        "aws.entrada_invalida",
        "entrada inválida para a API — revise parâmetros do conector",
    ),
    "ValidationException": (
        "aws.entrada_invalida",
        "entrada inválida para a API — revise parâmetros do conector",
    ),
    "ThrottlingException": (
        "aws.throttling",
        "limite de taxa AWS atingido — reduza concorrência e tente novamente",
    ),
    "TooManyRequestsException": (
        "aws.throttling",
        "limite de taxa AWS atingido — reduza concorrência e tente novamente",
    ),
    "ExpiredTokenException": (
        "aws.token_expirado",
        "credenciais temporárias expiraram — renove a sessão (sso login / refresh)",
    ),
}


def map_client_error(exc: Exception, *, context: str) -> AwsConnectorError:
    """Translate a botocore ClientError (or generic failure) to the taxonomy."""
    code = ""
    error_info: dict[str, Any] = getattr(exc, "response", {}).get("Error", {}) or {}
    code = error_info.get("Code", "")
    if code in _ERROR_MAP:
        domain_code, hint = _ERROR_MAP[code]
    else:
        name = type(exc).__name__
        if name in ("NoCredentialsError", "PartialCredentialsError"):
            domain_code, hint = (
                "aws.sem_credenciais",
                "credenciais indisponíveis — configure profile/env/IAM role/SSO",
            )
        elif name == "ProfileNotFound":
            domain_code, hint = (
                "aws.perfil_inexistente",
                "perfil AWS não existe — confira ~/.aws/config ou use --profile válido",
            )
        elif name in ("ConnectTimeoutError", "ReadTimeoutError", "EndpointConnectionError"):
            domain_code, hint = (
                "aws.timeout",
                "timeout ao alcançar a AWS — confira rede/proxy/região",
            )
        elif name == "NoRegionError":
            domain_code, hint = (
                "aws.regiao_ausente",
                "região não configurada — use --region ou AWS_DEFAULT_REGION",
            )
        else:
            domain_code, hint = (
                "aws.erro_transitorio",
                "falha inesperada da API — pode ser transitório; tente novamente",
            )
    return AwsConnectorError(
        code=domain_code,
        message=f"{context}: {hint}",
        details={
            "context": context,
            "aws_error_code": code or type(exc).__name__,
            # aws error messages can embed request context; keep only the code.
        },
    )
