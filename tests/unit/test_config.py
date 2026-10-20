"""Unit tests for the configuration precedence chain."""

from pathlib import Path

import pytest

from data_sentinel.core.configuration import (
    REDACTED,
    SentinelConfig,
    load_config,
)
from data_sentinel.core.contracts import AnalysisMode
from data_sentinel.core.exceptions import ConfigurationError

CLEAN_ENV: dict[str, str] = {}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestDefaults:
    def test_defaults_when_no_files(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        cfg = load_config(cwd=tmp_path, env={"HOME": str(tmp_path)})
        assert cfg.profile is AnalysisMode.BALANCED
        assert cfg.log_level == "INFO"
        assert cfg.output_format == "text"
        assert cfg.redact_secrets is True

    def test_missing_files_tolerated(self, tmp_path: Path) -> None:
        cfg = load_config(cwd=tmp_path, env={"HOME": str(tmp_path)})
        layers = {s.layer: s for s in cfg.sources}
        assert layers["user"].found is False
        assert layers["project"].found is False
        assert layers["default"].applied is True


class TestPrecedence:
    def test_user_config_overrides_defaults(self, tmp_path: Path) -> None:
        write(
            tmp_path / ".config/data-sentinel/config.toml",
            'profile = "economy"\nlog_level = "DEBUG"\n',
        )
        cfg = load_config(cwd=tmp_path / "work", env={"HOME": str(tmp_path)})
        assert cfg.profile is AnalysisMode.ECONOMY
        assert cfg.log_level == "DEBUG"

    def test_project_config_overrides_user(self, tmp_path: Path) -> None:
        write(tmp_path / ".config/data-sentinel/config.toml", 'profile = "economy"')
        write(tmp_path / "proj/data-sentinel.toml", 'profile = "deep"')
        cfg = load_config(
            cwd=tmp_path / "proj/sub/dir", env={"HOME": str(tmp_path)}
        )
        assert cfg.profile is AnalysisMode.DEEP

    def test_project_config_discovered_upward(self, tmp_path: Path) -> None:
        write(tmp_path / "proj/data-sentinel.toml", 'log_level = "ERROR"')
        cfg = load_config(
            cwd=tmp_path / "proj/a/b/c", env={"HOME": str(tmp_path)}
        )
        assert cfg.log_level == "ERROR"
        project = next(s for s in cfg.sources if s.layer == "project")
        assert project.found and str(tmp_path / "proj") in (project.path or "")

    def test_env_overrides_project(self, tmp_path: Path) -> None:
        write(tmp_path / "data-sentinel.toml", 'profile = "deep"')
        cfg = load_config(
            cwd=tmp_path,
            env={
                "HOME": str(tmp_path / "nohome"),
                "DATA_SENTINEL_PROFILE": "offline",
            },
        )
        assert cfg.profile is AnalysisMode.OFFLINE

    def test_cli_overrides_env(self, tmp_path: Path) -> None:
        cfg = load_config(
            cwd=tmp_path,
            env={"DATA_SENTINEL_LOG_LEVEL": "ERROR"},
            cli_overrides={"log_level": "DEBUG"},
        )
        assert cfg.log_level == "DEBUG"

    def test_unrelated_env_ignored(self, tmp_path: Path) -> None:
        cfg = load_config(
            cwd=tmp_path,
            env={"DATA_SENTINEL_UNKNOWN_KEY": "x", "OTHER": "y"},
        )
        assert not hasattr(cfg, "unknown_key")


class TestValidation:
    def test_invalid_profile_rejected(self, tmp_path: Path) -> None:
        write(tmp_path / "data-sentinel.toml", 'profile = "ultra"')
        with pytest.raises(ConfigurationError) as err:
            load_config(cwd=tmp_path, env={})
        assert "configuração inválida" in err.value.message
        assert err.value.code == "config.invalido"

    def test_invalid_toml_rejected(self, tmp_path: Path) -> None:
        write(tmp_path / "data-sentinel.toml", "profile = [broken")
        with pytest.raises(ConfigurationError) as err:
            load_config(cwd=tmp_path, env={})
        assert err.value.code == "config.toml_invalido"

    def test_invalid_env_value_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigurationError):
            load_config(
                cwd=tmp_path, env={"DATA_SENTINEL_MAX_FILE_BYTES": "-5"}
            )

    def test_max_file_bytes_must_be_positive(self, tmp_path: Path) -> None:
        write(tmp_path / "data-sentinel.toml", "max_file_bytes = 0")
        with pytest.raises(ConfigurationError):
            load_config(cwd=tmp_path, env={})


class TestRedaction:
    def test_secret_extra_keys_redacted(self) -> None:
        cfg = SentinelConfig.model_validate(
            {
                "profile": "balanced",
                "aws_secret_access_key": "AKIA123",
                "nested": {"api_token": "abc", "ok": "v"},
            }
        )
        dumped = cfg.to_redacted_dict()
        assert dumped["aws_secret_access_key"] == REDACTED
        assert dumped["nested"]["api_token"] == REDACTED
        assert dumped["nested"]["ok"] == "v"

    def test_repr_does_not_leak_secrets(self) -> None:
        cfg = SentinelConfig.model_validate({"my_password": "hunter2"})
        assert "hunter2" not in repr(cfg)
        assert REDACTED in repr(cfg)


class TestProfiles:
    def test_all_profiles_have_limits(self) -> None:
        for mode in AnalysisMode:
            cfg = SentinelConfig(profile=mode)
            limits = cfg.effective_limits()
            assert limits.max_file_bytes > 0

    def test_offline_disallows_network(self) -> None:
        cfg = SentinelConfig(profile=AnalysisMode.OFFLINE)
        assert cfg.effective_limits().allow_network is False

    def test_explicit_limit_beats_profile_default(self) -> None:
        cfg = SentinelConfig(profile=AnalysisMode.ECONOMY, max_file_bytes=1)
        assert cfg.effective_limits().max_file_bytes == 1
