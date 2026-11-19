"""cycle 16.1 wave-11 — ``forge/InstallLifecycle/v1`` compatibility +
incremental reinstall accounting.

Every receipt/health doc the service emits carries a ``lifecycle`` block
(``forge/InstallLifecycle/v1``): the state is derived from the receipt's
own evidence, never asserted by the writer. ``status`` stays the coarse
operation verdict; ``lifecycle.state`` is the honest finer position.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_sentinel.installation import lifecycle, service

LIFECYCLE_SCHEMA = "forge/InstallLifecycle/v1"


def _install(root: Path, host: str = "claude") -> dict:
    return service.install(
        host=host,
        scope="project",
        root=root,
        profile="recommended",
        yes=True,
    )


def _assert_block(doc: dict, state: str) -> dict:
    block = doc.get("lifecycle")
    assert isinstance(block, dict), f"missing lifecycle block in {doc.get('schema')}"
    assert block["schema"] == LIFECYCLE_SCHEMA
    assert block["state"] in lifecycle.STATES
    if state:
        assert block["state"] == state
    assert isinstance(block["detail"], str) and block["detail"]
    return block


# ---------------------------------------------------------------------------
# vendored module provenance
# ---------------------------------------------------------------------------


def test_lifecycle_vendored_stamp() -> None:
    """Drift gate: the vendored copy names its upstream source sha."""
    assert lifecycle._SOURCE_SHA256 not in ("", "canonical")
    assert len(lifecycle._SOURCE_SHA256) >= 12


def test_lifecycle_matches_canonical_when_sibling_present() -> None:
    """Byte-parity modulo the provenance stamp — when the canonical
    the-forge checkout is a sibling, drift is a defect, not a refactor."""
    canonical = (
        Path(__file__).resolve().parents[4]
        / "the-forge" / "src" / "theforge" / "install" / "lifecycle.py"
    )
    if not canonical.is_file():
        pytest.skip("requires sibling the-forge checkout (FORJAS workspace layout)")
    canon = canonical.read_text(encoding="utf-8")
    vend = (
        Path(__file__).resolve().parents[3]
        / "src" / "data_sentinel" / "installation" / "lifecycle.py"
    ).read_text(encoding="utf-8")
    # Drop the vendored-provenance stamp block (comment lines + constant +
    # the blank line it adds before the next import).
    import re

    vend = re.sub(
        r"# Vendored copy[^\n]*\n(?:#[^\n]*\n)*_SOURCE_SHA256[^\n]*\n\n\n",
        "",
        vend,
        count=1,
    )
    assert vend == canon


def test_lifecycle_module_derives_states() -> None:
    state, _ = lifecycle.receipt_state(
        {"status": "completed", "verification": {"status": "PASS"}}
    )
    assert state == "verified"
    state, _ = lifecycle.receipt_state({"status": "planned"})
    assert state == "planned"
    state, _ = lifecycle.receipt_state(
        {"status": "completed", "verification": {"status": "FAIL"}}
    )
    assert state == "failed"
    state, _ = lifecycle.health_state({"status": "healthy"})
    assert state == "ready"
    state, _ = lifecycle.health_state({"status": "unverified"})
    assert state == "unverified"


# ---------------------------------------------------------------------------
# lifecycle block on every emitted doc
# ---------------------------------------------------------------------------


def test_install_dry_run_plan_carries_lifecycle(tmp_path: Path) -> None:
    plan = service.install(
        host="claude", scope="project", root=tmp_path, dry_run=True
    )
    _assert_block(plan, "planned")
    assert list(tmp_path.rglob("*")) == []


def test_install_receipt_carries_lifecycle(tmp_path: Path) -> None:
    receipt = _install(tmp_path)
    _assert_block(receipt, "verified")
    # The persisted receipt file carries the same block (not only stdout).
    receipts = sorted((tmp_path / ".data-sentinel/install/receipts").glob("*.json"))
    assert receipts
    persisted = json.loads(receipts[-1].read_text(encoding="utf-8"))
    _assert_block(persisted, "verified")


def test_status_and_doctor_carry_lifecycle(tmp_path: Path) -> None:
    _install(tmp_path)
    st = service.status(root=tmp_path)
    _assert_block(st, "ready")
    doc = service.doctor(root=tmp_path)
    _assert_block(doc, "ready")


def test_status_unverified_pristine_root(tmp_path: Path) -> None:
    st = service.status(root=tmp_path)
    _assert_block(st, "unverified")


def test_repair_receipt_carries_lifecycle(tmp_path: Path) -> None:
    _install(tmp_path)
    dry = service.repair(root=tmp_path, dry_run=True)
    _assert_block(dry, "ready")
    doc = service.repair(root=tmp_path)
    assert doc["operation"] == "repair"
    _assert_block(doc, "verified")


def test_uninstall_receipt_carries_lifecycle(tmp_path: Path) -> None:
    _install(tmp_path)
    dry = service.uninstall(root=tmp_path, dry_run=True)
    _assert_block(dry, "planned")
    doc = service.uninstall(root=tmp_path)
    _assert_block(doc, "verified")


def test_mcp_verify_health_carries_lifecycle() -> None:
    doc = service.mcp_verify()
    block = _assert_block(doc, "")
    assert block["state"] in {"ready", "partially_applied", "unverified", "failed"}


# ---------------------------------------------------------------------------
# incremental reinstall (cycle 16.1 §7.4)
# ---------------------------------------------------------------------------


def test_incremental_reinstall_touches_nothing(tmp_path: Path) -> None:
    first = _install(tmp_path)
    assert first["status"] == "completed"
    counts1 = first["counts"]
    assert counts1["written"] > 0 and counts1["written_bytes"] > 0

    before = {
        p: (p.stat().st_mtime_ns, p.read_bytes())
        for p in tmp_path.rglob("*")
        if p.is_file() and ".data-sentinel" not in p.parts and ".forge" not in p.parts
    }
    second = _install(tmp_path)
    assert second["status"] == "completed"
    counts2 = second["counts"]
    # Honest accounting: nothing was actually re-written on reinstall.
    assert counts2["written"] == 0, counts2
    assert counts2["written_bytes"] == 0, counts2
    assert counts2.get("unchanged", 0) == counts1["written"]
    # Unchanged managed assets are not re-touched (mtime + bytes stable).
    for rel, (mtime, data) in before.items():
        assert rel.stat().st_mtime_ns == mtime, rel
        assert rel.read_bytes() == data, rel


def test_incremental_reinstall_rewrites_only_drift(tmp_path: Path) -> None:
    _install(tmp_path)
    drifted = tmp_path / ".claude/skills/data-sentinel-report/SKILL.md"
    drifted.write_text("corrupted", encoding="utf-8")
    second = _install(tmp_path)
    counts = second["counts"]
    assert counts["written"] == 1
    assert counts.get("updated") == 1
    assert counts["written_bytes"] > 0
    # The rest stayed byte-identical.
    assert counts.get("unchanged", 0) > 0


# ---------------------------------------------------------------------------
# mcp_command_resolved — PATH-independent argv (§9.3)
# ---------------------------------------------------------------------------


def test_resolved_mcp_command_falls_back_to_module() -> None:
    spec = service._spec()
    argv = service._resolved_mcp_command(spec)
    assert argv is not None
    if argv[1:2] == ("-m",):
        # No registered cli.shim → module-pinned interpreter argv.
        assert Path(argv[0]).is_absolute()
        assert argv[2] == "data_sentinel"
        assert argv[3:] == ("mcp", "serve")
    else:
        # Registered bootstrap shim — absolute by contract.
        assert Path(argv[0]).is_absolute()
        assert argv[1:] == ("mcp", "serve")


def test_resolved_mcp_command_prefers_registered_shim(tmp_path: Path, monkeypatch) -> None:
    shim = tmp_path / "bin" / "data-sentinel"
    monkeypatch.setattr(
        service,
        "_installation_manifest",
        lambda: {"cli": {"name": "data-sentinel", "shim": str(shim)}},
    )
    argv = service._resolved_mcp_command(service._spec())
    assert argv == (str(shim), "mcp", "serve")


def test_resolved_mcp_command_none_without_command() -> None:
    import dataclasses

    spec = dataclasses.replace(service._spec(), mcp_command=())
    assert service._resolved_mcp_command(spec) is None


def test_register_preserves_cli_shim(tmp_path: Path, monkeypatch) -> None:
    """A bootstrap-registered cli.shim survives `install` re-registering."""
    shim = str(tmp_path / "bin" / "data-sentinel")
    written: dict = {}
    monkeypatch.setattr(
        service,
        "_installation_manifest",
        lambda: {
            "cli": {
                "name": "data-sentinel",
                "version_cmd": ["data-sentinel", "--version"],
                "shim": shim,
            }
        },
    )
    monkeypatch.setattr(
        service.kit, "register_installation", lambda doc: written.update(doc)
    )
    ctx = service._ctx("project", tmp_path, (), "recommended", dry_run=True)
    service._register(ctx)
    assert written["cli"]["shim"] == shim
    assert written["cli"]["name"] == "data-sentinel"


# ---------------------------------------------------------------------------
# L0 boot — compact forge block, honest context metadata
# ---------------------------------------------------------------------------


def test_installed_agents_block_is_compact_l0(tmp_path: Path) -> None:
    """The AGENTS.md `forge:` block is the routing-critical minimum —
    identity, domains, manifest pointer. CLI/MCP/discovery detail lives in
    AGENT_PROTOCOL.md + the capability manifest, not duplicated here
    (cycle 16.1 §8.1)."""
    _install(tmp_path)
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    block = text.split("forge:data-sentinel-forge:begin")[1].split(
        "forge:data-sentinel-forge:end"
    )[0]
    assert "Capability manifest:" in block
    assert "data-sentinel-forge.json" in block
    # Compact L0: no duplicated CLI/MCP/discovery surface in the block.
    assert "Discovery:" not in block
    assert "MCP server:" not in block


def test_context_registry_marks_docs_only_install(tmp_path: Path) -> None:
    """A registry entry with an empty kit ledger still reports installed —
    the registry is the authoritative 'installed here' signal."""
    _install(tmp_path)
    ledger_file = tmp_path / ".data-sentinel/install/install-ledger.json"
    ledger_file.write_text('{"entries": {}}', encoding="utf-8")
    st = service.status(root=tmp_path)
    assert st["status"] == "healthy"
    assert st["context_registered"] is True
    _assert_block(st, "ready")
    doc = service.doctor(root=tmp_path)
    assert doc["status"] == "healthy"
    assert doc["context_registered"] is True
    ledger_check = next(c for c in doc["checks"] if c["id"] == "ledger")
    assert ledger_check["status"] == "NOT_APPLICABLE"
    ctx_check = next(c for c in doc["checks"] if c["id"] == "context-registry")
    assert ctx_check["status"] == "PASS"
