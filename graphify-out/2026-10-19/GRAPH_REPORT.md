# Graph Report - data-sentinel-forge  (2026-10-19)

## Corpus Check
- 89 files · ~18,211 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 925 nodes · 1013 edges · 47 communities (43 shown, 4 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `335b9230`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- enum
- properties
- ExecutionContext.schema.json
- Environment
- properties
- properties
- enum
- properties
- Evidence.schema.json
- properties
- properties
- ExecutionMetadata.schema.json
- properties
- properties
- exceptions/__init__.py
- test_contracts.py
- Environment
- contracts/__init__.py
- ResourceContext.schema.json
- entities.py
- ResourceContext
- CapabilityManifest.schema.json
- Environment.schema.json
- RequestConstraints.schema.json
- ArtifactReference.schema.json
- ArtifactReference
- AccessMetadata.schema.json
- RequestConstraints
- $defs
- ExecutionMetadata
- enum
- enum
- Review — ds-0001 Repository foundation and toolchain
- ds-0001.md
- TestValidation
- ds-0001.review.claude.md
- ds-0002.implement.claude.md
- Review — ds-0002 Core domain contracts and versioning
- enum
- ds-0002.md
- max_file_bytes
- timeout_seconds
- TestEnums
- scripts/__init__.py
- Platform
- data-sentinel

## God Nodes (most connected - your core abstractions)
1. `ContractModel` - 21 edges
2. `enum` - 15 edges
3. `enum` - 15 edges
4. `SentinelError` - 11 edges
5. `Platform` - 8 edges
6. `DiagnosticRequest` - 8 edges
7. `enum` - 8 edges
8. `enum` - 8 edges
9. `$defs` - 8 edges
10. `enum` - 8 edges

## Surprising Connections (you probably didn't know these)
- `sample_request()` --calls--> `DiagnosticRequest`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py
- `Evidence` --uses--> `EvidenceProvenance`  [INFERRED]
  src/data_sentinel/core/contracts/entities.py → src/data_sentinel/core/contracts/enums.py
- `ExecutionMetadata` --uses--> `ExecutionStatus`  [INFERRED]
  src/data_sentinel/core/contracts/entities.py → src/data_sentinel/core/contracts/enums.py
- `sample_report()` --calls--> `DiagnosticReport`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py
- `sample_evidence()` --calls--> `Evidence`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py

## Import Cycles
- None detected.

## Communities (47 total, 4 thin omitted)

### Community 0 - "enum"
Cohesion: 0.04
Nodes (48): $defs, Finding, FindingCategory, FindingStatus, Severity, additionalProperties, description, required (+40 more)

### Community 1 - "properties"
Cohesion: 0.04
Nodes (46): proposed_change, rationale, target, additionalProperties, description, anyOf, default, title (+38 more)

### Community 2 - "ExecutionContext.schema.json"
Cohesion: 0.05
Nodes (43): additionalProperties, type, anyOf, default, title, $defs, Environment, description (+35 more)

### Community 3 - "Environment"
Cohesion: 0.05
Nodes (42): type, anyOf, default, title, Environment, ExecutionContext, additionalProperties, title (+34 more)

### Community 4 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, items, title, type, $ref, description, items, title (+33 more)

### Community 5 - "properties"
Cohesion: 0.06
Nodes (39): items, title, type, $ref, items, title, type, minLength (+31 more)

### Community 6 - "enum"
Cohesion: 0.05
Nodes (38): $defs, FindingCategory, FindingStatus, Severity, description, enum, title, type (+30 more)

### Community 7 - "properties"
Cohesion: 0.05
Nodes (36): artifact_references, source_type, additionalProperties, default, $ref, items, minItems, title (+28 more)

### Community 8 - "Evidence.schema.json"
Cohesion: 0.05
Nodes (36): captured_at, confidence, content_hash, declared, observed, provenance, sanitized_excerpt, source (+28 more)

### Community 9 - "properties"
Cohesion: 0.06
Nodes (35): created_at, request_id, additionalProperties, format, title, type, description, anyOf (+27 more)

### Community 10 - "properties"
Cohesion: 0.06
Nodes (33): anyOf, default, format, title, type, maximum, minimum, title (+25 more)

### Community 11 - "ExecutionMetadata.schema.json"
Cohesion: 0.06
Nodes (30): CANCELLED, FAILED, RUNNING, SUCCEEDED, additionalProperties, $defs, ExecutionStatus, Platform (+22 more)

### Community 12 - "properties"
Cohesion: 0.08
Nodes (29): title, type, $ref, type, items, title, type, properties (+21 more)

### Community 13 - "properties"
Cohesion: 0.07
Nodes (29): anyOf, default, title, anyOf, default, title, $ref, properties (+21 more)

### Community 14 - "exceptions/__init__.py"
Cohesion: 0.13
Nodes (19): Exception, AnalyzerError, ConfigurationError, ContractValidationError, InputValidationError, PathViolationError, PersistenceError, Any (+11 more)

### Community 15 - "test_contracts.py"
Cohesion: 0.10
Nodes (19): Finding, export_schemas(), Path, Export JSON Schemas for the public contracts into schemas/. Usage: uv run…, DiagnosticReport, Evidence, A traceable excerpt supporting findings (§4)., Versioned output contract aggregating findings (§4). (+11 more)

### Community 16 - "Environment"
Cohesion: 0.08
Nodes (25): type, additionalProperties, title, type, Environment, additionalProperties, title, type (+17 more)

### Community 17 - "contracts/__init__.py"
Cohesion: 0.15
Nodes (23): DiagnosticRequest, Finding, Input describing what should be analyzed and how (§4)., An evidence-backed diagnostic conclusion (§4)., AnalysisMode, EvidenceProvenance, ExecutionStatus, FindingCategory (+15 more)

### Community 18 - "ResourceContext.schema.json"
Cohesion: 0.08
Nodes (23): additionalProperties, type, description, additionalProperties, title, type, anyOf, default (+15 more)

### Community 19 - "entities.py"
Cohesion: 0.11
Nodes (20): BaseModel, datetime, Self, AccessMetadata, ArtifactReference, ContractModel, _ensure_utc(), Environment (+12 more)

### Community 20 - "ResourceContext"
Cohesion: 0.09
Nodes (23): type, ResourceContext, additionalProperties, title, type, anyOf, default, title (+15 more)

### Community 21 - "CapabilityManifest.schema.json"
Cohesion: 0.09
Nodes (21): capability_id, version, additionalProperties, $defs, Platform, description, athena, aws_glue (+13 more)

### Community 22 - "Environment.schema.json"
Cohesion: 0.09
Nodes (21): additionalProperties, type, description, additionalProperties, title, type, name, minLength (+13 more)

### Community 23 - "RequestConstraints.schema.json"
Cohesion: 0.10
Nodes (19): additionalProperties, items, title, type, description, type, anyOf, default (+11 more)

### Community 24 - "ArtifactReference.schema.json"
Cohesion: 0.12
Nodes (16): additionalProperties, description, anyOf, default, title, uri, properties, description (+8 more)

### Community 25 - "ArtifactReference"
Cohesion: 0.12
Nodes (16): additionalProperties, description, properties, required, title, type, ArtifactReference, anyOf (+8 more)

### Community 26 - "AccessMetadata.schema.json"
Cohesion: 0.13
Nodes (14): anyOf, default, title, anyOf, default, title, additionalProperties, description (+6 more)

### Community 27 - "RequestConstraints"
Cohesion: 0.18
Nodes (11): items, title, type, RequestConstraints, type, allowed_roots, additionalProperties, description (+3 more)

### Community 28 - "$defs"
Cohesion: 0.22
Nodes (9): description, title, type, $defs, AnalysisMode, SourceType, description, title (+1 more)

### Community 29 - "ExecutionMetadata"
Cohesion: 0.20
Nodes (8): CapabilityManifest, ExecutionMetadata, OptimizationRecommendation, A proposed change with rationale, risk and rollback (§4)., Metadata about the job run the artifacts came from (§4)., Declared capabilities and limitations of an analyzer/component (§4)., sample_request(), TestConstruction

### Community 30 - "enum"
Cohesion: 0.25
Nodes (8): config, log, metrics, other, physical_plan, spark_event_log, sql_query, enum

### Community 31 - "enum"
Cohesion: 0.25
Nodes (8): athena, aws_glue, databricks, generic, iceberg, spark, trino, enum

### Community 32 - "Review — ds-0001 Repository foundation and toolchain"
Cohesion: 0.33
Nodes (5): Acceptance criteria check, Findings / notes, Review — ds-0001 Repository foundation and toolchain, Verdict, Verification evidence

### Community 33 - "ds-0001.md"
Cohesion: 0.33
Nodes (5): Acceptance Criteria, Constraints, Context, Grill Gate, Review Notes

### Community 35 - "ds-0001.review.claude.md"
Cohesion: 0.40
Nodes (4): Acceptance Criteria, Constraints, Context, Review Notes

### Community 36 - "ds-0002.implement.claude.md"
Cohesion: 0.40
Nodes (4): Acceptance Criteria, Constraints, Context, Review Notes

### Community 37 - "Review — ds-0002 Core domain contracts and versioning"
Cohesion: 0.40
Nodes (4): Acceptance criteria check, Notes, Review — ds-0002 Core domain contracts and versioning, Verdict

### Community 38 - "enum"
Cohesion: 0.40
Nodes (5): balanced, deep, economy, offline, enum

### Community 39 - "ds-0002.md"
Cohesion: 0.33
Nodes (5): Acceptance Criteria, Constraints, Context, Grill Gate, Review Notes

### Community 40 - "max_file_bytes"
Cohesion: 0.50
Nodes (4): anyOf, default, title, max_file_bytes

### Community 41 - "timeout_seconds"
Cohesion: 0.50
Nodes (4): timeout_seconds, anyOf, default, title

### Community 44 - "Platform"
Cohesion: 0.50
Nodes (4): Platform, description, title, type

## Knowledge Gaps
- **556 isolated node(s):** `Grill Gate`, `Context`, `Acceptance Criteria`, `Constraints`, `Review Notes` (+551 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `$defs` connect `$defs` to `Environment`, `properties`, `Platform`, `ArtifactReference`, `RequestConstraints`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `$defs` connect `enum` to `Environment`, `properties`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Why does `properties` connect `properties` to `Environment`, `properties`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **What connects `Grill Gate`, `Context`, `Acceptance Criteria` to the rest of the system?**
  _556 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `enum` be split into smaller, more focused modules?**
  _Cohesion score 0.0425531914893617 - nodes in this community are weakly interconnected._
- **Should `properties` be split into smaller, more focused modules?**
  _Cohesion score 0.0425531914893617 - nodes in this community are weakly interconnected._
- **Should `ExecutionContext.schema.json` be split into smaller, more focused modules?**
  _Cohesion score 0.046511627906976744 - nodes in this community are weakly interconnected._