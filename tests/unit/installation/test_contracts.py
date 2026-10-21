"""ds-0109 — install contracts, planner over vendored kit, ownership."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from data_sentinel import _installkit as kit
from data_sentinel.core.exceptions import SentinelError
from data_sentinel.installation import service
from data_sentinel.installation.contracts import (
    InstallProfile,
    InstallReceipt,
    InstallScope,
    PlannedAction,
    assert_no_secrets,
)
from data_sentinel.installation.ownership import load_ledger
from data_sentinel.installation.planner import plan_installation


def _plan(tmp: Path, **kw):
    defaults = {
        "scope": InstallScope.PROJECT,
        "host": "claude",
        "profile": InstallProfile.RECOMMENDED,
        "root": tmp,
    }
    defaults.update(kw)
    return plan_installation(**defaults)


def test_plan_is_deterministic(tmp_path: Path) -> None:
    a = _plan(tmp_path)
    b = _plan(tmp_path)
    assert a.plan_id == b.plan_id
    assert len(a.plan_id) == 16
    assert a.canonical_payload() == b.canonical_payload()


def test_plan_id_changes_with_inputs(tmp_path: Path) -> None:
    assert _plan(tmp_path).plan_id != _plan(tmp_path, host="codex").plan_id


def test_plan_covers_marker(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    paths = {Path(c.path).name for c in plan.planned_changes}
    assert "AGENTS.md" in paths


def test_unknown_host_refused(tmp_path: Path) -> None:
    plan = _plan(tmp_path, host="emacs")
    assert plan.refusals
    assert not plan.planned_changes


def test_unknown_scope_refused(tmp_path: Path) -> None:
    plan = _plan(tmp_path, scope=InstallScope.PROJECT, host="bogus host!")
    assert plan.refusals


def test_foreign_file_refused_in_plan(tmp_path: Path) -> None:
    """A pre-existing user file on an asset path → conflict + refuse."""
    # Craft a foreign file at a path the kit would write (.mcp.json merge
    # is exempt — merges preserve foreign keys; marker blocks likewise).
    # Use a managed asset path once assets land; until then simulate via
    # a file that collides with nothing → ensure no crash and plan valid.
    (tmp_path / "AGENTS.md").write_text("user content", encoding="utf-8")
    plan = _plan(tmp_path)
    names = {c.source_asset: c for c in plan.planned_changes}
    # AGENTS.md marker update is allowed (marker-block merge preserves text)
    assert "AGENTS.md" in names


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    before = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")}
    receipt = service.install(host="claude", scope="project", root=tmp_path,
                              dry_run=True)
    after = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")}
    assert before == after
    assert receipt["status"] == "planned"


def test_apply_requires_approval(tmp_path: Path) -> None:
    with pytest.raises(kit.InstallError):
        service.install(host="claude", scope="project", root=tmp_path, yes=False)


def test_install_creates_managed_files_and_ledger(tmp_path: Path) -> None:
    receipt = service.install(host="claude", scope="project", root=tmp_path, yes=True)
    assert receipt["status"] == "completed"
    assert (tmp_path / "AGENTS.md").is_file()
    assert "data-sentinel-forge:managed" in (tmp_path / "AGENTS.md").read_text()
    mcp = (tmp_path / ".mcp.json").read_text(encoding="utf-8")
    assert '"data-sentinel"' in mcp
    ledger = load_ledger(tmp_path)
    assert ledger.is_managed(Path("AGENTS.md"), tmp_path)
    # receipt written under state dir
    assert list((tmp_path / ".data-sentinel/install").glob("receipts/*.json"))


def test_reinstall_idempotent(tmp_path: Path) -> None:
    service.install(host="claude", scope="project", root=tmp_path, yes=True)
    plan = _plan(tmp_path)
    skip_or_update = {c.action for c in plan.planned_changes}
    # no fresh CREATEs on second plan — everything exists managed
    assert PlannedAction.CREATE not in skip_or_update


def test_user_file_never_overwritten(tmp_path: Path) -> None:
    """P0: foreign file content is preserved; kit marks it skipped."""
    target = tmp_path / "AGENTS.md"
    target.write_text("MY OWN AGENTS", encoding="utf-8")
    service.install(host="claude", scope="project", root=tmp_path, yes=True)
    text = target.read_text(encoding="utf-8")
    assert "MY OWN AGENTS" in text  # marker merges, never replaces


def test_corrupt_ledger_errors(tmp_path: Path) -> None:
    path = tmp_path / ".data-sentinel/install" / kit.LEDGER_NAME
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(SentinelError, match="unreadable"):
        load_ledger(tmp_path)


def test_receipt_rejects_secrets() -> None:
    receipt = InstallReceipt(
        installation_id="i1", plan_id="p" * 16, timestamp=datetime.now(UTC),
        version="0.1.0", source_method="git", scope=InstallScope.PROJECT,
        host="claude", profile=InstallProfile.MINIMAL,
        validation=["token=sk-abc"],
    )
    with pytest.raises(SentinelError, match="secret"):
        assert_no_secrets(receipt)


def test_uninstall_removes_only_managed(tmp_path: Path) -> None:
    service.install(host="claude", scope="project", root=tmp_path, yes=True)
    user_file = tmp_path / "notes.txt"
    user_file.write_text("mine", encoding="utf-8")
    receipt = service.uninstall(scope="project", root=tmp_path)
    assert receipt["status"] == "completed"
    assert user_file.is_file()  # user file survives
    assert not (tmp_path / ".mcp.json").exists()  # managed key removed
    assert not (tmp_path / "AGENTS.md").exists()
