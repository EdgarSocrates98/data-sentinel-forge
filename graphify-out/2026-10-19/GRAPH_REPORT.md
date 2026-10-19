# Graph Report - data-sentinel-forge  (2026-10-19)

## Corpus Check
- 104 files · ~22,666 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1070 nodes · 1274 edges · 55 communities (50 shown, 5 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 61 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0726aa0d`
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
- enum
- properties
- properties
- exceptions/__init__.py
- test_contracts.py
- Environment
- contracts/__init__.py
- ResourceContext.schema.json
- ContractModel
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
- safe_resolve
- ds-0002.md
- entities.py
- enum
- enum
- scripts/__init__.py
- ds-0003.md
- data-sentinel
- ds-0004.implement.claude.md
- Review — ds-0004 Security primitives
- enum
- SourceType
- max_file_bytes
- timeout_seconds
- TestEnums
- Evidence

## God Nodes (most connected - your core abstractions)
1. `load_config()` - 25 edges
2. `ContractModel` - 21 edges
3. `safe_resolve()` - 15 edges
4. `enum` - 15 edges
5. `enum` - 15 edges
6. `read_input_file()` - 14 edges
7. `SentinelConfig` - 13 edges
8. `SentinelError` - 11 edges
9. `redact_secrets()` - 10 edges
10. `TestSafeResolve` - 9 edges

## Surprising Connections (you probably didn't know these)
- `sample_request()` --calls--> `DiagnosticRequest`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py
- `sample_report()` --calls--> `DiagnosticReport`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py
- `sample_evidence()` --calls--> `Evidence`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py
- `safe_resolve()` --calls--> `PathViolationError`  [INFERRED]
  src/data_sentinel/core/security/paths.py → src/data_sentinel/core/exceptions/__init__.py
- `Evidence` --uses--> `EvidenceProvenance`  [INFERRED]
  src/data_sentinel/core/contracts/entities.py → src/data_sentinel/core/contracts/enums.py

## Import Cycles
- None detected.

## Communities (55 total, 5 thin omitted)

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
Cohesion: 0.17
Nodes (13): Exception, AnalyzerError, PathViolationError, PersistenceError, Any, Domain exceptions with structured error information., A request violated a security guard (paths, secrets, limits)., A file path resolved outside the allowed roots. (+5 more)

### Community 15 - "test_contracts.py"
Cohesion: 0.11
Nodes (17): Finding, export_schemas(), Path, Export JSON Schemas for the public contracts into schemas/. Usage: uv run…, parametrize, Path, Contract tests: exported JSON Schemas validate serialized examples., test_example_validates_against_schema() (+9 more)

### Community 16 - "Environment"
Cohesion: 0.08
Nodes (25): type, additionalProperties, title, type, Environment, additionalProperties, title, type (+17 more)

### Community 17 - "contracts/__init__.py"
Cohesion: 0.15
Nodes (23): DiagnosticRequest, Finding, Input describing what should be analyzed and how (§4)., An evidence-backed diagnostic conclusion (§4)., AnalysisMode, EvidenceProvenance, ExecutionStatus, FindingCategory (+15 more)

### Community 18 - "ResourceContext.schema.json"
Cohesion: 0.08
Nodes (23): additionalProperties, type, description, additionalProperties, title, type, anyOf, default (+15 more)

### Community 19 - "ContractModel"
Cohesion: 0.15
Nodes (12): Self, AccessMetadata, ContractModel, ExecutionContext, Any, Observed resource shape of a workload execution., Base for public contracts: forbid unknown fields, stable JSON, domain errors., How an evidence artifact was accessed. (+4 more)

### Community 20 - "load_config"
Cohesion: 0.07
Nodes (36): BaseModel, Configuration system with documented precedence (§01.5)., _discover_project_config(), _env_overrides(), load_config(), _load_toml(), _merge(), Any (+28 more)

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
Nodes (9): description, title, type, $defs, AnalysisMode, Platform, description, title (+1 more)

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

### Community 38 - "safe_resolve"
Cohesion: 0.06
Nodes (31): fixture, MonkeyPatch, parametrize, InputValidationError, User-supplied input is invalid or unsafe to process., Security primitives: path guard, file-input guard, sanitization, redaction., InputFile, _looks_binary() (+23 more)

### Community 39 - "ds-0002.md"
Cohesion: 0.33
Nodes (5): Acceptance Criteria, Constraints, Context, Grill Gate, Review Notes

### Community 40 - "entities.py"
Cohesion: 0.17
Nodes (11): datetime, ArtifactReference, DiagnosticReport, _ensure_utc(), Environment, Data Sentinel public domain entities (§4 contracts). Every model serializes to…, Limits the caller imposes on the analysis., Versioned output contract aggregating findings (§4). (+3 more)

### Community 41 - "enum"
Cohesion: 0.25
Nodes (8): config, log, metrics, other, physical_plan, spark_event_log, sql_query, enum

### Community 42 - "enum"
Cohesion: 0.25
Nodes (8): athena, aws_glue, databricks, generic, iceberg, spark, trino, enum

### Community 44 - "ds-0003.md"
Cohesion: 0.33
Nodes (5): Acceptance Criteria, Constraints, Context, Grill Gate, Review Notes

### Community 47 - "ds-0004.implement.claude.md"
Cohesion: 0.40
Nodes (4): Acceptance Criteria, Constraints, Context, Review Notes

### Community 48 - "Review — ds-0004 Security primitives"
Cohesion: 0.40
Nodes (4): Acceptance criteria check, Findings / notes, Review — ds-0004 Security primitives, Verdict

### Community 49 - "enum"
Cohesion: 0.40
Nodes (5): balanced, deep, economy, offline, enum

### Community 50 - "SourceType"
Cohesion: 0.50
Nodes (4): SourceType, description, title, type

### Community 51 - "max_file_bytes"
Cohesion: 0.50
Nodes (4): anyOf, default, title, max_file_bytes

### Community 52 - "timeout_seconds"
Cohesion: 0.50
Nodes (4): timeout_seconds, anyOf, default, title

## Knowledge Gaps
- **575 isolated node(s):** `Context`, `Acceptance Criteria`, `Constraints`, `Review Notes`, `Acceptance criteria check` (+570 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `$defs` connect `enum` to `Environment`, `properties`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `InputValidationError` connect `safe_resolve` to `exceptions/__init__.py`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `$defs` connect `$defs` to `Environment`, `properties`, `SourceType`, `ArtifactReference`, `RequestConstraints`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `load_config()` (e.g. with `SentinelConfig` and `ConfigurationError`) actually correct?**
  _`load_config()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `safe_resolve()` (e.g. with `InputValidationError` and `PathViolationError`) actually correct?**
  _`safe_resolve()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Context`, `Acceptance Criteria`, `Constraints` to the rest of the system?**
  _575 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `enum` be split into smaller, more focused modules?**
  _Cohesion score 0.0425531914893617 - nodes in this community are weakly interconnected._