"""ds-0118 §13.4 — golden plan fixtures for the scope x host x profile matrix.

The normalized plan (sorted path/kind/action/sha256 tuples) is fully
deterministic: asset bytes are pinned by sha256, so the golden catches
any drift in rendering, per-host layout, or profile gating. Regenerate
with `UPDATE_GOLDEN=1 uv run pytest tests/e2e/test_install_golden.py`.
"""

import json
import os
from pathlib import Path

import pytest

from data_sentinel.installation import service

GOLDEN = (
    Path(__file__).resolve().parents[2]
    / "tests/fixtures/installation/plan-matrix.json"
)

SCOPES = ("project", "workspace")
HOSTS = ("claude", "devin", "codex", "copilot", "cursor")
PROFILES = ("minimal", "recommended", "full")


def _matrix(tmp: Path) -> dict:
    out: dict[str, object] = {}
    for scope in SCOPES:
        for host in HOSTS:
            for profile in PROFILES:
                root = tmp / f"{scope}-{host}-{profile}"
                if scope == "user":
                    root = root / "home"
                doc = service.install(
                    host=host,
                    scope=scope,
                    root=root,
                    profile=profile,
                    yes=True,
                    dry_run=True,
                )
                key = f"{scope}|{host}|{profile}"
                out[key] = {
                    "status": doc["status"],
                    "components": doc["components"],
                    "planned_files": sorted(
                        (
                            {
                                "path": f["path"],
                                "kind": f["kind"],
                                "action": f["action"],
                                "sha256": f["sha256"],
                            }
                            for f in doc["planned_files"]
                        ),
                        key=lambda f: f["path"],
                    ),
                    "planned_markers": [
                        {"file": m["file"], "marker": m["marker"]}
                        for m in doc.get("planned_markers", [])
                    ],
                }
    return out


def test_plan_matrix_matches_golden(tmp_path: Path) -> None:
    actual = _matrix(tmp_path)
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        pytest.skip("golden regenerated")
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == golden
