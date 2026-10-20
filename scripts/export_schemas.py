"""Export JSON Schemas for the public contracts into schemas/.

Usage: uv run python scripts/export_schemas.py [out_dir]
"""

import json
import sys
from pathlib import Path
from typing import Any

from data_sentinel.core.contracts import (
    AccessContext,
    AccessMetadata,
    ArtifactReference,
    CapabilityManifest,
    CompatibilityAssessment,
    DiagnosticReport,
    DiagnosticRequest,
    Environment,
    Evidence,
    ExecutionContext,
    ExecutionMetadata,
    Finding,
    IcebergSnapshotSummary,
    IcebergTableMetadata,
    LakehouseOperation,
    OptimizationRecommendation,
    RequestConstraints,
    ResourceContext,
    ExternalDiagnosticBundle,
    CapabilityDescriptor,
)

ENTITIES: dict[str, Any] = {
    cls.__name__: cls
    for cls in (
        DiagnosticRequest,
        Evidence,
        Finding,
        DiagnosticReport,
        OptimizationRecommendation,
        ExecutionMetadata,
        CapabilityManifest,
        ArtifactReference,
        AccessMetadata,
        Environment,
        ExecutionContext,
        AccessContext,
        CompatibilityAssessment,
        IcebergSnapshotSummary,
        IcebergTableMetadata,
        LakehouseOperation,
        RequestConstraints,
        ResourceContext,
        ExternalDiagnosticBundle,
        CapabilityDescriptor,
    )
}


def export_schemas(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, model in ENTITIES.items():
        schema = model.model_json_schema()
        schema.setdefault("$schema", "https://json-schema.org/draft/2020-12/schema")
        path = out_dir / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("schemas")
    for path in export_schemas(target):
        print(path)
