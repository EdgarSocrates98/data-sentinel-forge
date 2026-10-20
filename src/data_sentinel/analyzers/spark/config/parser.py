"""Spark config parsing from properties/--conf/Glue-arg formats (§8.2).

Every entry records its provenance (properties_file | conf_fragment |
glue_arguments | explicit_dict).
"""

import json
import re
from dataclasses import dataclass

_CONF_RE = re.compile(r"--conf[=\s]+([^=\s]+)=([^\s]+)")
_PROP_RE = re.compile(r"^([^#\s=]+)\s*=\s*(.*)$")
_GLUE_KEY_RE = re.compile(r"^--")


@dataclass(frozen=True)
class ConfigEntry:
    key: str
    value: str
    provenance: str  # properties_file | conf_fragment | glue_arguments | explicit_dict


def parse_config_text(text: str, *, filename: str = "") -> list[ConfigEntry]:
    """Parse properties lines and/or --conf fragments from raw text."""
    out: list[ConfigEntry] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        conf = _CONF_RE.findall(line)
        if conf:
            out.extend(
                ConfigEntry(k, v, "conf_fragment") for k, v in conf
            )
            continue
        m = _PROP_RE.match(line)
        if m:
            out.append(ConfigEntry(m.group(1), m.group(2).strip(), "properties_file"))
    return out


def parse_glue_arguments(text: str) -> list[ConfigEntry]:
    """Glue job default args JSON: {"--conf": "a=b c=d", "--key": "val"}."""
    out: list[ConfigEntry] = []
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return out
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if not isinstance(v, str):
            continue
        if k == "--conf":
            out.extend(
                ConfigEntry(kk, vv, "glue_arguments")
                for kk, vv in (p.split("=", 1) for p in v.split() if "=" in p)
            )
        elif k.startswith("--") and (k[2:] == "conf" or ".sql." in k or "spark." in k):
            out.append(ConfigEntry(k.lstrip("-"), v, "glue_arguments"))
    return out
