"""Configuration loading with documented precedence (§01.5).

Precedence (highest wins): CLI overrides > DATA_SENTINEL_* env vars >
project ``data-sentinel.toml`` (discovered upward from cwd) >
user ``$XDG_CONFIG_HOME/data-sentinel/config.toml`` > defaults.
"""

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from data_sentinel.core.configuration.models import (
    ConfigSource,
    SentinelConfig,
    env_field_name,
)
from data_sentinel.core.exceptions import ConfigurationError

PROJECT_CONFIG_NAME = "data-sentinel.toml"
USER_CONFIG_NAME = "data-sentinel/config.toml"


def _user_config_path(env: Mapping[str, str]) -> Path:
    xdg = env.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path(env.get("HOME", str(Path.home()))) / ".config"
    return base / USER_CONFIG_NAME


def _discover_project_config(cwd: Path) -> Path | None:
    for directory in (cwd, *cwd.parents):
        candidate = directory / PROJECT_CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def _load_toml(path: Path, layer: str) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(
            code="config.toml_invalido",
            message=f"arquivo de configuração inválido em {path}: {exc}",
            details={"path": str(path), "layer": layer},
        ) from exc
    except OSError as exc:
        raise ConfigurationError(
            code="config.leitura_falhou",
            message=f"não foi possível ler o arquivo de configuração {path}: {exc}",
            details={"path": str(path), "layer": layer},
        ) from exc
    if not isinstance(data, dict):
        return {}
    return data


def _merge(base: dict[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Recursive merge: overlay keys win, nested dicts merge key by key."""
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _env_overrides(env: Mapping[str, str], model: type[SentinelConfig]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for name, raw in env.items():
        field = env_field_name(name)
        if field is None or field not in model.model_fields or field == "sources":
            continue
        overrides[field] = raw
    return overrides


def load_config(
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    cli_overrides: Mapping[str, Any] | None = None,
) -> SentinelConfig:
    """Resolve SentinelConfig across all precedence layers.

    ``cwd``/``env`` are injectable for testing; ``cli_overrides`` lets the
    command layer apply the highest precedence layer.
    """
    env_map: Mapping[str, str] = os.environ if env is None else env
    start = (cwd or Path.cwd()).resolve()
    sources: list[ConfigSource] = []

    merged: dict[str, Any] = {}
    sources.append(ConfigSource(layer="default", applied=True))

    user_path = _user_config_path(env_map)
    if user_path.is_file():
        merged = _merge(merged, _load_toml(user_path, "user"))
        sources.append(
            ConfigSource(layer="user", path=str(user_path), found=True, applied=True)
        )
    else:
        sources.append(ConfigSource(layer="user", path=str(user_path), found=False))

    project_path = _discover_project_config(start)
    if project_path is not None:
        merged = _merge(merged, _load_toml(project_path, "project"))
        sources.append(
            ConfigSource(
                layer="project", path=str(project_path), found=True, applied=True
            )
        )
    else:
        sources.append(ConfigSource(layer="project", found=False))

    env_overrides = _env_overrides(env_map, SentinelConfig)
    if env_overrides:
        merged = _merge(merged, env_overrides)
    sources.append(
        ConfigSource(layer="env", applied=bool(env_overrides), found=bool(env_overrides))
    )

    if cli_overrides:
        cli = {k: v for k, v in cli_overrides.items() if v is not None}
        if cli:
            merged = _merge(merged, cli)
        sources.append(ConfigSource(layer="cli", applied=bool(cli), found=bool(cli)))

    try:
        config = SentinelConfig.model_validate(merged)
    except ValidationError as exc:
        raise ConfigurationError(
            code="config.invalido",
            message="configuração inválida: " + "; ".join(
                f"campo '{'.'.join(str(p) for p in e['loc'])}' {e['msg']}"
                for e in exc.errors(include_url=False)
            ),
            details={"errors": exc.errors(include_url=False)},
        ) from exc
    config.sources = sources
    return config
