"""Iceberg metadata.json tolerant parser (§3.1-3.2, §3.8).

Parses table metadata for format versions 1, 2 and 3. Unknown fields are
preserved in `extras` — never dropped, never turned into fake diagnoses.
Pure JSON parsing: no URL fetching, no script execution, size-capped.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

MAX_METADATA_BYTES = 16 * 1024 * 1024  # §3.8 — cap oversized metadata
MAX_SNAPSHOTS = 10_000
MAX_DEPTH = 64


class MetadataParseError(ValueError):
    """Malformed/unreadable Iceberg metadata — becomes a limitation."""


@dataclass
class SchemaField:
    field_id: int
    name: str
    type_repr: str
    required: bool


@dataclass
class SchemaInfo:
    schema_id: int
    fields: list[SchemaField] = field(default_factory=list)


@dataclass
class PartitionField:
    source_id: int
    field_id: int
    name: str
    transform: str


@dataclass
class PartitionSpec:
    spec_id: int
    fields: list[PartitionField] = field(default_factory=list)


@dataclass
class SnapshotInfo:
    snapshot_id: int
    parent_snapshot_id: int | None
    timestamp_ms: int | None
    operation: str
    sequence_number: int | None
    summary: dict[str, Any]
    manifest_list: str


@dataclass
class TableMetadata:
    format_version: int
    table_uuid: str
    location: str
    metadata_location: str
    current_snapshot_id: int | None
    schemas: list[SchemaInfo]
    current_schema_id: int | None
    partition_specs: list[PartitionSpec]
    default_spec_id: int | None
    sort_order_id: int | None
    snapshots: list[SnapshotInfo]
    snapshot_log: list[dict[str, Any]]
    properties: dict[str, str]
    refs: dict[str, Any]
    extras: dict[str, Any]  # unknown top-level fields preserved
    warnings: list[str] = field(default_factory=list)


_KNOWN_TOP = {
    "format-version", "table-uuid", "location", "last-updated-ms",
    "last-column-id", "schemas", "current-schema-id", "partition-specs",
    "default-spec-id", "last-partition-id", "properties", "current-snapshot-id",
    "snapshots", "snapshot-log", "metadata-log", "sort-orders",
    "default-sort-order-id", "refs", "statistics", "partition-statistics",
}


def _depth(obj: Any, d: int = 0) -> int:
    if d > MAX_DEPTH:
        return d
    if isinstance(obj, dict):
        return max((_depth(v, d + 1) for v in obj.values()), default=d)
    if isinstance(obj, list):
        return max((_depth(v, d + 1) for v in obj), default=d)
    return d


def _schema_fields(node: dict[str, Any]) -> list[SchemaField]:
    out: list[SchemaField] = []
    fields = node.get("fields")
    if not isinstance(fields, list):
        return out
    for f in fields:
        if not isinstance(f, dict):
            continue
        t = f.get("type")
        out.append(
            SchemaField(
                field_id=int(f.get("id", -1)),
                name=str(f.get("name", "?")),
                type_repr=t if isinstance(t, str) else json.dumps(t, sort_keys=True)[:80],
                required=bool(f.get("required", False)),
            )
        )
    return out


def _spec_fields(node: dict[str, Any]) -> list[PartitionField]:
    out: list[PartitionField] = []
    for f in node.get("fields") or []:
        if not isinstance(f, dict):
            continue
        out.append(
            PartitionField(
                source_id=int(f.get("source-id", -1)),
                field_id=int(f.get("field-id", -1)),
                name=str(f.get("name", "?")),
                transform=str(f.get("transform", "identity")),
            )
        )
    return out


def parse_metadata(text: str, *, source: str = "") -> TableMetadata:
    """Parse Iceberg table metadata JSON. Never raises on bad input shape —
    raises MetadataParseError only for non-JSON / oversized / cyclic input."""
    if len(text.encode()) > MAX_METADATA_BYTES:
        raise MetadataParseError(
            f"metadata excede {MAX_METADATA_BYTES} bytes — recusado por segurança"
        )
    try:
        raw: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MetadataParseError(f"JSON inválido: {exc}") from exc
    if not isinstance(raw, dict):
        raise MetadataParseError("metadata Iceberg deve ser um objeto JSON")
    if _depth(raw) > MAX_DEPTH:
        raise MetadataParseError("metadata com profundidade suspeita — possível referência cíclica")

    warnings: list[str] = []
    fmt = raw.get("format-version")
    if fmt not in (1, 2, 3):
        warnings.append(
            f"format-version '{fmt}' não reconhecida (suportadas: 1, 2, 3) — "
            "campos conhecidos ainda serão lidos"
        )

    schemas = [
        SchemaInfo(schema_id=int(s.get("schema-id", -1)), fields=_schema_fields(s))
        for s in raw.get("schemas") or []
        if isinstance(s, dict)
    ]
    specs = [
        PartitionSpec(spec_id=int(s.get("spec-id", 0)), fields=_spec_fields(s))
        for s in raw.get("partition-specs") or []
        if isinstance(s, dict)
    ]

    snapshots: list[SnapshotInfo] = []
    raw_snaps = raw.get("snapshots") or []
    if len(raw_snaps) > MAX_SNAPSHOTS:
        warnings.append(
            f"{len(raw_snaps)} snapshots excedem o limite {MAX_SNAPSHOTS} — truncado"
        )
        raw_snaps = raw_snaps[:MAX_SNAPSHOTS]
    for s in raw_snaps:
        if not isinstance(s, dict):
            continue
        snapshots.append(
            SnapshotInfo(
                snapshot_id=int(s.get("snapshot-id", -1)),
                parent_snapshot_id=(
                    int(s["parent-snapshot-id"])
                    if s.get("parent-snapshot-id") is not None
                    else None
                ),
                timestamp_ms=(
                    int(s["timestamp-ms"]) if s.get("timestamp-ms") is not None else None
                ),
                operation=str(s.get("operation", "")),
                sequence_number=(
                    int(s["sequence-number"]) if s.get("sequence-number") is not None else None
                ),
                summary=dict(s["summary"]) if isinstance(s.get("summary"), dict) else {},
                manifest_list=str(s.get("manifest-list", "")),
            )
        )

    props = raw.get("properties")
    refs = raw.get("refs")
    extras = {k: v for k, v in raw.items() if k not in _KNOWN_TOP}
    loc = str(raw.get("location", ""))
    if re.match(r"^(https?|file)://", loc):
        warnings.append(
            f"location '{loc[:40]}' usa esquema não-S3 — o parser NÃO segue URLs; "
            "somente o conteúdo fornecido é analisado"
        )

    return TableMetadata(
        format_version=int(fmt) if fmt in (1, 2, 3) else -1,
        table_uuid=str(raw.get("table-uuid", "")),
        location=loc,
        metadata_location=source,
        current_snapshot_id=(
            int(raw["current-snapshot-id"])
            if raw.get("current-snapshot-id") is not None
            else None
        ),
        schemas=schemas,
        current_schema_id=(
            int(raw["current-schema-id"]) if raw.get("current-schema-id") is not None else None
        ),
        partition_specs=specs,
        default_spec_id=(
            int(raw["default-spec-id"]) if raw.get("default-spec-id") is not None else None
        ),
        sort_order_id=(
            int(raw["default-sort-order-id"])
            if raw.get("default-sort-order-id") is not None
            else None
        ),
        snapshots=snapshots,
        snapshot_log=[e for e in (raw.get("snapshot-log") or []) if isinstance(e, dict)],
        properties={str(k): str(v) for k, v in props.items()} if isinstance(props, dict) else {},
        refs=refs if isinstance(refs, dict) else {},
        extras=extras,
        warnings=warnings,
    )
