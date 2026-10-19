"""Contract tests: exported JSON Schemas validate serialized examples."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from scripts.export_schemas import ENTITIES, export_schemas

from data_sentinel.core.contracts import (
    CapabilityManifest,
    ExecutionMetadata,
    OptimizationRecommendation,
    Platform,
)
from tests.unit.test_contracts import (
    sample_evidence,
    sample_finding,
    sample_report,
    sample_request,
)

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"

EXAMPLES = {
    "DiagnosticRequest": lambda: sample_request(),
    "Evidence": lambda: sample_evidence(),
    "Finding": lambda: sample_finding(),
    "DiagnosticReport": lambda: sample_report(),
    "OptimizationRecommendation": lambda: OptimizationRecommendation(
        target="t", proposed_change="c", rationale="r"
    ),
    "ExecutionMetadata": lambda: ExecutionMetadata(platform=Platform.SPARK),
    "CapabilityManifest": lambda: CapabilityManifest(capability_id="c", version="0.1.0"),
}

MAIN_ENTITIES = list(EXAMPLES)


def test_committed_schemas_cover_main_entities() -> None:
    for name in MAIN_ENTITIES:
        assert (SCHEMA_DIR / f"{name}.schema.json").is_file(), f"missing schema: {name}"


@pytest.mark.parametrize("name", MAIN_ENTITIES)
def test_example_validates_against_schema(name: str) -> None:
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text())
    instance = json.loads(EXAMPLES[name]().to_json())
    Draft202012Validator(schema).validate(instance)


def test_exported_schemas_are_stable(tmp_path: Path) -> None:
    export_schemas(tmp_path)
    for name in ENTITIES:
        regenerated = (tmp_path / f"{name}.schema.json").read_text()
        committed = (SCHEMA_DIR / f"{name}.schema.json").read_text()
        assert regenerated == committed, f"schema drift for {name}"
