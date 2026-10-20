"""EMR security checks (ds-0069, §13)."""

import os
from pathlib import Path

import pytest

from data_sentinel.agents.guardrails import GuardrailError, PermissionClass, check_tool_permission
from data_sentinel.connectors.aws.emr import ALLOWED_ACTIONS


def test_emr_allowlist_read_only() -> None:
    mutating = [a for a in ALLOWED_ACTIONS
                if not a.startswith(("list", "describe", "get"))]
    assert not mutating


def test_emr_tools_no_write_permission() -> None:
    from data_sentinel.tools.registry import build_default_registry
    reg = build_default_registry()
    for t in reg.list_tools():
        if t.tool_id.startswith("sentinel.emr."):
            assert not t.network_required
            assert not t.side_effects


def test_emr_tool_denies_destructive() -> None:
    with pytest.raises(GuardrailError):
        check_tool_permission("sentinel.emr.analyze_ec2",
                              PermissionClass.DESTRUCTIVE)


def test_no_secrets_in_fixtures() -> None:
    for f in Path("fixtures").rglob("emr*"):
        if not f.is_file():
            continue
        txt = f.read_text()
        assert "AKIA" not in txt
        assert "secret" not in txt.lower()
        assert "password" not in txt.lower()


@pytest.mark.skipif(
    os.getenv("DATA_SENTINEL_AWS_TESTS") != "1",
    reason="env-gated: requires real AWS non-prod credentials")
def test_real_emr_allowlist_call() -> None:
    """Real AWS: only allowlisted calls may be attempted."""
    import boto3

    from data_sentinel.connectors.aws.emr import EmrConnector
    conn = EmrConnector(boto3.Session())
    res = conn._call("list_clusters")
    assert "Clusters" in res
