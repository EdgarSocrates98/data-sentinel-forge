"""Hostile-input tests for the security primitives."""

import ast
from pathlib import Path

import pytest

from data_sentinel.core.exceptions import InputValidationError, PathViolationError
from data_sentinel.core.security import (
    InputFile,
    read_input_file,
    redact_secrets,
    safe_resolve,
    sanitize_evidence_excerpt,
    sanitize_log_text,
)

SRC_DIR = Path(__file__).resolve().parents[2] / "src"


@pytest.fixture()
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "inner").mkdir()
    (tmp_path / "inner/ok.log").write_text("hello log\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestSafeResolve:
    def test_allows_file_inside_cwd(self, workdir: Path) -> None:
        assert safe_resolve("inner/ok.log").is_file()

    def test_rejects_dotdot_escape(self, workdir: Path) -> None:
        (workdir.parent / "outside.log").write_text("x", encoding="utf-8")
        with pytest.raises(PathViolationError):
            safe_resolve("inner/../../outside.log")

    def test_rejects_absolute_outside_root(self, workdir: Path) -> None:
        with pytest.raises(PathViolationError):
            safe_resolve("/etc/hostname")

    def test_absolute_allowed_when_explicit_root(self, workdir: Path) -> None:
        outside = workdir.parent / "outside.log"
        outside.write_text("x", encoding="utf-8")
        resolved = safe_resolve(str(outside), allowed_roots=[workdir.parent])
        assert resolved == outside.resolve()

    def test_rejects_symlink_escape(self, workdir: Path) -> None:
        outside = workdir.parent / "secret.log"
        outside.write_text("x", encoding="utf-8")
        link = workdir / "inner/link.log"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("symlinks unavailable")
        with pytest.raises(PathViolationError):
            safe_resolve("inner/link.log")

    def test_rejects_nonexistent(self, workdir: Path) -> None:
        with pytest.raises(InputValidationError):
            safe_resolve("nope.log")

    def test_rejects_directory(self, workdir: Path) -> None:
        with pytest.raises(InputValidationError):
            safe_resolve("inner")

    def test_rejects_nul_byte(self, workdir: Path) -> None:
        with pytest.raises((InputValidationError, ValueError)):
            safe_resolve("inner/\x00evil.log")


class TestReadInputFile:
    def test_reads_utf8(self, workdir: Path) -> None:
        f = read_input_file("inner/ok.log", max_file_bytes=1024)
        assert isinstance(f, InputFile)
        assert "hello" in f.text

    def test_rejects_oversized(self, workdir: Path) -> None:
        big = workdir / "inner/big.log"
        big.write_bytes(b"a" * 2048)
        with pytest.raises(InputValidationError) as err:
            read_input_file("inner/big.log", max_file_bytes=1024)
        assert err.value.code == "entrada.arquivo_grande"

    def test_size_check_uses_real_size(self, workdir: Path) -> None:
        big = workdir / "inner/big.log"
        big.write_bytes(b"a" * 2048)
        with pytest.raises(InputValidationError):
            read_input_file("inner/big.log", max_file_bytes=1024)

    def test_rejects_binary(self, workdir: Path) -> None:
        blob = workdir / "inner/blob.bin"
        blob.write_bytes(b"\x00\x01\x02" * 400)
        with pytest.raises(InputValidationError) as err:
            read_input_file("inner/blob.bin", max_file_bytes=8192)
        assert err.value.code == "entrada.binario"

    def test_rejects_invalid_utf8(self, workdir: Path) -> None:
        bad = workdir / "inner/bad.log"
        bad.write_bytes(b"log \xff\xfe invalid\n")
        with pytest.raises(InputValidationError) as err:
            read_input_file("inner/bad.log", max_file_bytes=8192)
        assert err.value.code == "entrada.codificacao"

    def test_allow_binary_decodes_with_replacement(self, workdir: Path) -> None:
        bad = workdir / "inner/bad.log"
        bad.write_bytes(b"log \xff\xfe invalid\n")
        f = read_input_file("inner/bad.log", max_file_bytes=8192, allow_binary=True)
        assert "�" in f.text


class TestRedaction:
    @pytest.mark.parametrize(
        ("payload", "marker"),
        [
            ("key AKIAIOSFODNN7EXAMPLE in log", "aws-access-key-id"),
            ("ASIAIOSFODNN7EXAMPLE here", "aws-access-key-id"),
            ("aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "aws-secret-key"),
            ("password=hunter2", "secret"),
            ("db password: 's3cr3t!!'", "secret"),
            ("token=abcdef12345", "secret"),
            ("api_key: ABCDEF123456", "secret"),
            ("Authorization: Basic dXNlcjpwYXNz", "authorization"),
            ("Authorization: Bearer abcdef1234567890xyz", "bearer-token"),
            ("use ghp_" + "a" * 36 + " token", "token"),
            ("postgres://user:p%40ss@db.host:5432/x", "credentials"),
            ("amqp://admin:admin@rabbitmq/", "credentials"),
            ("xoxb-" + "1234567890-abc", "token"),
        ],
    )
    def test_secrets_redacted(self, payload: str, marker: str) -> None:
        out = redact_secrets(payload)
        assert "«redacted:" in out and marker in out

    @pytest.mark.parametrize(
        "payload",
        [
            "AKIAIOSFODNN7EXAMPLE",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "hunter2",
            "abcdef12345",
            "p%40ss",
        ],
    )
    def test_secret_values_do_not_survive(self, payload: str) -> None:
        text = {
            "hunter2": "password=hunter2",
            "abcdef12345": "token=abcdef12345",
            "p%40ss": "postgres://u:p%40ss@h/",
        }.get(payload, f"aws_secret_access_key={payload}")
        assert payload not in redact_secrets(text)

    def test_private_key_block_removed(self) -> None:
        text = (
            "log start\n-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIE\n-----END RSA PRIVATE KEY-----\nend"
        )
        out = redact_secrets(text)
        assert "MIIE" not in out
        assert "«redacted:private-key»" in out

    def test_benign_text_unchanged(self) -> None:
        text = "INFO executor 1 finished stage 42 with 0 failures"
        assert redact_secrets(text) == text

    def test_passwordless_url_unchanged(self) -> None:
        text = "reading s3://bucket/path/file.parquet"
        assert redact_secrets(text) == text


class TestSanitize:
    def test_strips_ansi(self) -> None:
        assert "\x1b" not in sanitize_log_text("\x1b[31mERROR\x1b[0m boom")
        assert "ERROR" in sanitize_log_text("\x1b[31mERROR\x1b[0m boom")

    def test_strips_control_keeps_newline_tab(self) -> None:
        out = sanitize_log_text("a\x00b\x07c\nd\te")
        assert "\x00" not in out and "\x07" not in out
        assert "\n" in out and "\t" in out

    def test_truncates_with_marker(self) -> None:
        out = sanitize_log_text("x" * 100, max_chars=10)
        assert len(out) < 100
        assert "truncado" in out

    def test_no_partial_secret_at_boundary(self) -> None:
        secret = "AKIA" + "Z" * 16
        text = "a" * 50 + " " + secret + " " + "b" * 50
        out = sanitize_evidence_excerpt(text, max_chars=60)
        assert secret[:20] not in out or "«redacted:" in out
        assert "AKIA" not in out

    def test_excerpt_is_sanitized_and_redacted(self) -> None:
        out = sanitize_evidence_excerpt("log \x1b[31mpassword=p4ssw0rd!\x1b[0m end")
        assert "p4ssw0rd" not in out
        assert "«redacted:" in out

    def test_empty_and_malformed_inputs(self) -> None:
        assert sanitize_evidence_excerpt("") == ""
        assert sanitize_log_text("\x00\x01") == ""


BANNED_IMPORTS = {"subprocess"}
BANNED_CALLS = {"eval", "exec", "system", "popen", "spawnl", "spawnv"}


def test_no_dangerous_calls_in_src() -> None:
    offenders: list[str] = []
    for file in SRC_DIR.rglob("*.py"):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = {a.name.split(".")[0] for a in node.names}
                module = getattr(node, "module", "") or ""
                if names & BANNED_IMPORTS or module.split(".")[0] in BANNED_IMPORTS:
                    offenders.append(f"{file}: banned import {names or module}")
            elif isinstance(node, ast.Call):
                func = node.func
                name = (
                    func.id
                    if isinstance(func, ast.Name)
                    else func.attr
                    if isinstance(func, ast.Attribute)
                    else ""
                )
                if name in BANNED_CALLS:
                    offenders.append(f"{file}:{node.lineno}: banned call {name}()")
    assert offenders == []


def test_src_has_no_os_system_usage() -> None:
    for file in SRC_DIR.rglob("*.py"):
        content = file.read_text(encoding="utf-8")
        assert "os.system(" not in content
        assert "os.popen(" not in content
