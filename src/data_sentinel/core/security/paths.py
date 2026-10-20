"""Path and file-input guards for untrusted artifacts (§01.7)."""

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from data_sentinel.core.exceptions import InputValidationError, PathViolationError

BINARY_SNIFF_BYTES = 8192


@dataclass(frozen=True)
class InputFile:
    """A validated, decoded input artifact."""

    path: Path
    text: str
    size_bytes: int


def safe_resolve(
    path: str | Path,
    *,
    allowed_roots: Iterable[str | Path] | None = None,
    must_exist: bool = True,
) -> Path:
    """Resolve ``path`` and ensure it stays inside an allowed root.

    Allowed roots default to the current working directory. Absolute paths
    outside it are accepted only when the caller explicitly lists them in
    ``allowed_roots`` (e.g. a user-supplied CLI argument).
    """
    try:
        # Resolve non-strict first so the allowed-roots check runs before
        # any filesystem existence check — an out-of-root path must be
        # rejected even when it does not exist (order-independent).
        candidate = Path(path).expanduser().resolve(strict=False)
    except (OSError, ValueError) as exc:
        raise InputValidationError(
            code="entrada.caminho_invalido",
            message=f"caminho inválido: {path!r} ({exc})",
            details={"path": repr(path)},
        ) from exc

    roots = (
        [Path(r).expanduser().resolve() for r in allowed_roots]
        if allowed_roots
        else [Path.cwd().resolve()]
    )
    if not any(candidate.is_relative_to(root) for root in roots):
        raise PathViolationError(
            code="seguranca.fora_das_raizes",
            message=f"caminho fora das raízes permitidas: {candidate}",
            details={
                "path": str(candidate),
                "allowed_roots": [str(r) for r in roots],
            },
        )
    if must_exist:
        if not candidate.exists():
            raise InputValidationError(
                code="entrada.nao_encontrada",
                message=f"arquivo não encontrado: {candidate}",
                details={"path": str(candidate)},
            )
        if not candidate.is_file():
            raise InputValidationError(
                code="entrada.nao_e_arquivo",
                message=f"não é um arquivo regular: {candidate}",
                details={"path": str(candidate)},
            )
    return candidate


def _looks_binary(sample: bytes) -> bool:
    if b"\x00" in sample:
        return True
    if not sample:
        return False
    text_chars = bytearray({7, 8, 9, 10, 11, 12, 13, 27} | set(range(0x20, 0x7F)))
    non_text = sample.translate(None, text_chars)
    return len(non_text) / len(sample) > 0.30


def read_input_file(
    path: str | Path,
    *,
    max_file_bytes: int,
    allowed_roots: Iterable[str | Path] | None = None,
    allow_binary: bool = False,
) -> InputFile:
    """Validate, size-check and decode an input file. Read-only."""
    resolved = safe_resolve(path, allowed_roots=allowed_roots)
    size = resolved.stat().st_size
    if size > max_file_bytes:
        raise InputValidationError(
            code="entrada.arquivo_grande",
            message=f"arquivo excede o limite de {max_file_bytes} bytes: {resolved} ({size} bytes)",
            details={
                "path": str(resolved),
                "size_bytes": size,
                "max_file_bytes": max_file_bytes,
            },
        )
    with resolved.open("rb") as handle:
        sample = handle.read(BINARY_SNIFF_BYTES)
        if _looks_binary(sample) and not allow_binary:
            raise InputValidationError(
                code="entrada.binario",
                message=f"arquivo parece binário e foi rejeitado: {resolved}",
                details={"path": str(resolved)},
            )
        handle.seek(0)
        raw = handle.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        if not allow_binary:
            raise InputValidationError(
                code="entrada.codificacao",
                message=f"arquivo não é UTF-8 válido: {resolved}",
                details={"path": str(resolved)},
            ) from exc
        text = raw.decode("utf-8", errors="replace")
    return InputFile(path=resolved, text=unicodedata.normalize("NFC", text), size_bytes=size)
