"""ds-0027 — lakehouse CLI group."""

from typer.testing import CliRunner

from data_sentinel.cli import app

r = CliRunner()


def test_metadata_cmd():
    res = r.invoke(app, ["lakehouse", "metadata", "-f",
                         "fixtures/iceberg/v2_evolved.json", "--no-persist", "--quiet"])
    assert res.exit_code == 0, res.output
    assert "achado" in res.output


def test_access_cmd():
    res = r.invoke(app, ["lakehouse", "access", "-f",
                         "fixtures/access/cross_write.json", "--no-persist", "--quiet"])
    assert res.exit_code == 0, res.output


def test_policy_cmd():
    res = r.invoke(app, ["lakehouse", "policy", "-f",
                         "fixtures/policies/cross_kms.json", "--no-persist", "--quiet"])
    assert res.exit_code == 0, res.output


def test_operation_cmd():
    res = r.invoke(app, ["lakehouse", "operation", "-f",
                         "fixtures/operations/merge_dups.json", "--no-persist", "--quiet"])
    assert res.exit_code == 0, res.output
    assert "CONFIRMED" in res.output


def test_compat_terminal():
    res = r.invoke(app, ["lakehouse", "compat", "--runtime", "glue-5.1",
                         "--operation", "merge", "--access-mode", "fgac"])
    assert res.exit_code == 0, res.output
    assert "SUPPORTED_WITH_CONSTRAINTS" in res.output


def test_compat_json():
    res = r.invoke(app, ["lakehouse", "compat", "--runtime", "glue-4.0",
                         "--operation", "select", "--table-format", "iceberg-v3",
                         "--json"])
    assert res.exit_code == 0, res.output
    assert "UNSUPPORTED" in res.output


def test_compat_unknown_mode_noted():
    res = r.invoke(app, ["lakehouse", "compat", "--runtime", "glue-5.1",
                         "--operation", "select"])
    assert "nunca é presumido" in res.output
