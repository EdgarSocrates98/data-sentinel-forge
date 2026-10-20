"""Capability discovery tests (ds-0035)."""

from typer.testing import CliRunner

from data_sentinel.cli import app
from data_sentinel.diagnostics.capabilities import all_descriptors

runner = CliRunner()


def test_descriptors_cover_analyzers_and_integrations() -> None:
    ds = all_descriptors()
    ids = [d.capability_id for d in ds]
    assert "sentinel.import.doctor-bundle" in ids
    assert "sentinel.incident.graph" in ids
    assert sum(1 for i in ids if i.startswith("sentinel.")
               and i not in ("sentinel.import.doctor-bundle",
                             "sentinel.incident.graph")) == 10
    assert ids == sorted(ids)  # determinístico


def test_cli_descriptors_json() -> None:
    r = runner.invoke(app, ["capabilities", "--descriptors"])
    assert r.exit_code == 0
    import json
    out = json.loads(r.stdout)
    assert all("capability_id" in d and "provider" in d for d in out)


def test_no_forge_imports_in_src() -> None:
    """Independência: src/ nunca importa pacotes forge_*."""
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[2] / "src" / "data_sentinel"
    for py in src.rglob("*.py"):
        for i, line in enumerate(py.read_text().splitlines(), 1):
            assert "import forge_" not in line and "from forge_" not in line, \
                f"{py}:{i} importa ecossistema forge"
