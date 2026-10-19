# Graph Report - data-sentinel-forge  (2026-10-19)

## Corpus Check
- 96 files · ~20,323 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 992 nodes · 1142 edges · 42 communities (39 shown, 3 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 32 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2dfc2d3a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- enum
- properties
- ExecutionContext.schema.json
- ExecutionContext
- properties
- properties
- enum
- properties
- Evidence.schema.json
- properties
- properties
- enum
- properties
- properties
- exceptions/__init__.py
- test_contracts.py
- properties
- contracts/__init__.py
- ResourceContext.schema.json
- entities.py
- load_config
- CapabilityManifest.schema.json
- Environment.schema.json
- RequestConstraints.schema.json
- ArtifactReference.schema.json
- ArtifactReference
- AccessMetadata.schema.json
- RequestConstraints
- $defs
- ExecutionMetadata
- ds-0003.implement.claude.md
- Review — ds-0003 Configuration system
- Review — ds-0001 Repository foundation and toolchain
- ds-0001.md
- TestValidation
- ds-0001.review.claude.md
- ds-0002.implement.claude.md
- Review — ds-0002 Core domain contracts and versioning
- ds-0002.md
- scripts/__init__.py
- data-sentinel

## God Nodes (most connected - your core abstractions)
1. `load_config()` - 25 edges
2. `ContractModel` - 21 edges
3. `enum` - 15 edges
4. `enum` - 15 edges
5. `SentinelConfig` - 13 edges
6. `SentinelError` - 11 edges
7. `write()` - 9 edges
8. `DiagnosticRequest` - 8 edges
9. `Platform` - 8 edges
10. `enum` - 8 edges

## Surprising Connections (you probably didn't know these)
- `sample_report()` --calls--> `DiagnosticReport`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py
- `sample_evidence()` --calls--> `Evidence`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py
- `sample_request()` --calls--> `DiagnosticRequest`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py
- `_load_toml()` --calls--> `ConfigurationError`  [INFERRED]
  src/data_sentinel/core/configuration/loader.py → src/data_sentinel/core/exceptions/__init__.py
- `load_config()` --calls--> `ConfigurationError`  [INFERRED]
  src/data_sentinel/core/configuration/loader.py → src/data_sentinel/core/exceptions/__init__.py

## Import Cycles
- None detected.

## Communities (42 total, 3 thin omitted)

### Community 0 - "enum"
Cohesion: 0.05
Nodes (45): $defs, Environment, FindingCategory, FindingStatus, Severity, additionalProperties, description, required (+37 more)

### Community 1 - "properties"
Cohesion: 0.04
Nodes (46): proposed_change, rationale, target, additionalProperties, description, anyOf, default, title (+38 more)

### Community 2 - "ExecutionContext.schema.json"
Cohesion: 0.05
Nodes (43): additionalProperties, type, anyOf, default, title, $defs, Environment, description (+35 more)

### Community 3 - "ExecutionContext"
Cohesion: 0.06
Nodes (35): type, anyOf, default, title, ExecutionContext, additionalProperties, title, type (+27 more)

### Community 4 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, items, title, type, $ref, description, items, title (+33 more)

### Community 5 - "properties"
Cohesion: 0.04
Nodes (49): items, title, type, $ref, Finding, items, title, type (+41 more)

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

### Community 11 - "enum"
Cohesion: 0.04
Nodes (46): CANCELLED, FAILED, RUNNING, SUCCEEDED, type, $defs, ExecutionStatus, Platform (+38 more)

### Community 12 - "properties"
Cohesion: 0.08
Nodes (29): title, type, $ref, type, items, title, type, properties (+21 more)

### Community 13 - "properties"
Cohesion: 0.05
Nodes (36): additionalProperties, description, anyOf, default, title, anyOf, default, title (+28 more)

### Community 14 - "exceptions/__init__.py"
Cohesion: 0.13
Nodes (19): Exception, AnalyzerError, ConfigurationError, ContractValidationError, InputValidationError, PathViolationError, PersistenceError, Any (+11 more)

### Community 15 - "test_contracts.py"
Cohesion: 0.09
Nodes (18): Finding, export_schemas(), Path, Export JSON Schemas for the public contracts into schemas/. Usage: uv run…, parametrize, Path, Contract tests: exported JSON Schemas validate serialized examples., test_example_validates_against_schema() (+10 more)

### Community 16 - "properties"
Cohesion: 0.11
Nodes (18): type, additionalProperties, title, type, additionalProperties, title, type, properties (+10 more)

### Community 17 - "contracts/__init__.py"
Cohesion: 0.15
Nodes (23): DiagnosticRequest, Finding, Input describing what should be analyzed and how (§4)., An evidence-backed diagnostic conclusion (§4)., AnalysisMode, EvidenceProvenance, ExecutionStatus, FindingCategory (+15 more)

### Community 18 - "ResourceContext.schema.json"
Cohesion: 0.08
Nodes (23): additionalProperties, type, description, additionalProperties, title, type, anyOf, default (+15 more)

### Community 19 - "entities.py"
Cohesion: 0.10
Nodes (23): datetime, Self, AccessMetadata, ArtifactReference, ContractModel, DiagnosticReport, _ensure_utc(), Environment (+15 more)

### Community 20 - "load_config"
Cohesion: 0.07
Nodes (34): BaseModel, Configuration system with documented precedence (§01.5)., _discover_project_config(), _env_overrides(), load_config(), _load_toml(), _merge(), Any (+26 more)

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
Cohesion: 0.11
Nodes (19): items, title, type, RequestConstraints, type, anyOf, default, title (+11 more)

### Community 28 - "$defs"
Cohesion: 0.05
Nodes (41): balanced, config, deep, economy, log, metrics, offline, other (+33 more)

### Community 29 - "ExecutionMetadata"
Cohesion: 0.29
Nodes (6): CapabilityManifest, ExecutionMetadata, OptimizationRecommendation, A proposed change with rationale, risk and rollback (§4)., Metadata about the job run the artifacts came from (§4)., Declared capabilities and limitations of an analyzer/component (§4).

### Community 30 - "ds-0003.implement.claude.md"
Cohesion: 0.40
Nodes (4): Acceptance Criteria, Constraints, Context, Review Notes

### Community 31 - "Review — ds-0003 Configuration system"
Cohesion: 0.40
Nodes (4): Acceptance criteria check, Findings / notes, Review — ds-0003 Configuration system, Verdict

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

### Community 39 - "ds-0002.md"
Cohesion: 0.33
Nodes (5): Acceptance Criteria, Constraints, Context, Grill Gate, Review Notes

## Knowledge Gaps
- **563 isolated node(s):** `Context`, `Acceptance Criteria`, `Constraints`, `Review Notes`, `Acceptance criteria check` (+558 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `$defs` connect `$defs` to `RequestConstraints`, `ArtifactReference`, `ExecutionContext`, `properties`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `$defs` connect `enum` to `properties`, `properties`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `properties` connect `properties` to `properties`, `properties`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `load_config()` (e.g. with `SentinelConfig` and `ConfigurationError`) actually correct?**
  _`load_config()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `SentinelConfig` (e.g. with `_env_overrides()` and `load_config()`) actually correct?**
  _`SentinelConfig` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Context`, `Acceptance Criteria`, `Constraints` to the rest of the system?**
  _563 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `enum` be split into smaller, more focused modules?**
  _Cohesion score 0.045454545454545456 - nodes in this community are weakly interconnected._