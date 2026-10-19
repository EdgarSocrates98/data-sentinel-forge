# Graph Report - data-sentinel-forge  (2026-10-19)

## Corpus Check
- 115 files · ~25,757 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1166 nodes · 1431 edges · 81 communities (77 shown, 4 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 74 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a880a4ec`
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
- AccessMetadata
- properties
- properties
- enum
- type
- properties
- SentinelError
- test_contracts.py
- Environment
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
- read_input_file
- ds-0002.md
- SparkGlueLogAnalyzer
- enum
- enum
- scripts/__init__.py
- ds-0003.md
- data-sentinel
- ds-0004.implement.claude.md
- Review — ds-0004 Security primitives
- enum
- .analyze
- max_file_bytes
- timeout_seconds
- Analyzer
- Finding
- enum
- analyzers/__init__.py
- DiagnosticReport.schema.json
- type
- FindingStatus
- enum
- TestValidationAndRegistry
- properties
- ds-0004.md
- ds-0005.implement.claude.md
- Review — ds-0005 Analyzer protocol + Spark/Glue log analyzer
- Platform
- supported_platforms
- $defs
- findings
- limitations
- required_permissions
- created_at
- evidence_ids
- explanation
- limitations
- recommendations
- summary
- validation_steps
- Platform
- .validate_input

## God Nodes (most connected - your core abstractions)
1. `load_config()` - 25 edges
2. `Analyzer` - 21 edges
3. `ContractModel` - 21 edges
4. `read_input_file()` - 16 edges
5. `SparkGlueLogAnalyzer` - 15 edges
6. `safe_resolve()` - 15 edges
7. `enum` - 15 edges
8. `enum` - 15 edges
9. `SentinelError` - 13 edges
10. `SentinelConfig` - 13 edges

## Surprising Connections (you probably didn't know these)
- `TestValidationAndRegistry` --uses--> `AnalyzerRegistry`  [INFERRED]
  tests/unit/test_log_analyzer.py → src/data_sentinel/analyzers/registry.py
- `inputs_for()` --calls--> `read_input_file()`  [INFERRED]
  tests/unit/test_log_analyzer.py → src/data_sentinel/core/security/paths.py
- `sample_request()` --calls--> `DiagnosticRequest`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py
- `sample_report()` --calls--> `DiagnosticReport`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py
- `sample_evidence()` --calls--> `Evidence`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py

## Import Cycles
- None detected.

## Communities (81 total, 4 thin omitted)

### Community 0 - "enum"
Cohesion: 0.14
Nodes (14): enum, configuration, cost, data_quality, data_skew, dependency, disk_space, executor_loss (+6 more)

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
Cohesion: 0.20
Nodes (10): $ref, title, type, properties, category, finding_id, severity, status (+2 more)

### Community 6 - "enum"
Cohesion: 0.05
Nodes (38): $defs, FindingCategory, FindingStatus, Severity, description, enum, title, type (+30 more)

### Community 7 - "properties"
Cohesion: 0.05
Nodes (36): artifact_references, source_type, additionalProperties, default, $ref, items, minItems, title (+28 more)

### Community 8 - "AccessMetadata"
Cohesion: 0.09
Nodes (23): declared, observed, static_inferred, anyOf, default, title, anyOf, default (+15 more)

### Community 9 - "properties"
Cohesion: 0.14
Nodes (14): anyOf, default, properties, environment, report_id, request_id, schema_version, title (+6 more)

### Community 10 - "properties"
Cohesion: 0.04
Nodes (46): captured_at, confidence, content_hash, provenance, sanitized_excerpt, source, source_location, anyOf (+38 more)

### Community 11 - "enum"
Cohesion: 0.04
Nodes (46): CANCELLED, FAILED, RUNNING, SUCCEEDED, type, $defs, ExecutionStatus, Platform (+38 more)

### Community 12 - "type"
Cohesion: 0.22
Nodes (9): type, supported_operations, supported_runtimes, items, title, type, items, title (+1 more)

### Community 13 - "properties"
Cohesion: 0.05
Nodes (36): additionalProperties, description, anyOf, default, title, anyOf, default, title (+28 more)

### Community 14 - "SentinelError"
Cohesion: 0.13
Nodes (17): Exception, AnalyzerError, ContractValidationError, InputValidationError, PathViolationError, PersistenceError, Any, Domain exceptions with structured error information. (+9 more)

### Community 15 - "test_contracts.py"
Cohesion: 0.09
Nodes (18): Finding, export_schemas(), Path, Export JSON Schemas for the public contracts into schemas/. Usage: uv run…, parametrize, Path, Contract tests: exported JSON Schemas validate serialized examples., test_example_validates_against_schema() (+10 more)

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
Cohesion: 0.10
Nodes (23): datetime, Self, AccessMetadata, ArtifactReference, ContractModel, DiagnosticReport, _ensure_utc(), Environment (+15 more)

### Community 20 - "load_config"
Cohesion: 0.07
Nodes (36): BaseModel, Configuration system with documented precedence (§01.5)., _discover_project_config(), _env_overrides(), load_config(), _load_toml(), _merge(), Any (+28 more)

### Community 21 - "CapabilityManifest.schema.json"
Cohesion: 0.22
Nodes (8): capability_id, version, additionalProperties, description, required, $schema, title, type

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

### Community 38 - "read_input_file"
Cohesion: 0.06
Nodes (31): fixture, MonkeyPatch, parametrize, DiagnosticRequest, InputFile, Security primitives: path guard, file-input guard, sanitization, redaction., InputFile, _looks_binary() (+23 more)

### Community 39 - "ds-0002.md"
Cohesion: 0.33
Nodes (5): Acceptance Criteria, Constraints, Context, Grill Gate, Review Notes

### Community 40 - "SparkGlueLogAnalyzer"
Cohesion: 0.13
Nodes (10): Pattern, Spark/AWS Glue analyzers., CapabilityManifest, SourceType, Deterministic log analyzer for Spark and AWS Glue artifacts (§01.3)., Regex/heuristic classifier over Spark/Glue log4j-style output. Never fabricates…, SparkGlueLogAnalyzer, LogPattern (+2 more)

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

### Community 50 - ".analyze"
Cohesion: 0.22
Nodes (9): FindingStatus, Path, Run the deterministic pass. Never fabricates findings., inputs_for(), DiagnosticRequest, SourceType, Unit + integration tests for the Spark/Glue log analyzer., request_for() (+1 more)

### Community 51 - "max_file_bytes"
Cohesion: 0.50
Nodes (4): anyOf, default, title, max_file_bytes

### Community 52 - "timeout_seconds"
Cohesion: 0.50
Nodes (4): timeout_seconds, anyOf, default, title

### Community 53 - "Analyzer"
Cohesion: 0.17
Nodes (6): Analyzer, SourceType, Deterministic, local, read-only analyzer contract., AnalyzerRegistry, SourceType, In-memory registry of available analyzers.

### Community 54 - "Finding"
Cohesion: 0.20
Nodes (10): Finding, additionalProperties, description, required, title, type, category, explanation (+2 more)

### Community 55 - "enum"
Cohesion: 0.20
Nodes (10): Severity, CRITICAL, HIGH, INFO, LOW, MEDIUM, description, enum (+2 more)

### Community 56 - "analyzers/__init__.py"
Cohesion: 0.28
Nodes (6): ABC, Analyzer package: protocol, registry, and built-in analyzers., AnalysisResult, Analyzer protocol: the stable interface every analyzer implements (§01.3)., Internal output of one analyzer pass over one request. Not a wire contract —…, Analyzer registry: registration, discovery, lookup by source type.

### Community 57 - "DiagnosticReport.schema.json"
Cohesion: 0.22
Nodes (8): created_at, request_id, additionalProperties, description, required, $schema, title, type

### Community 58 - "type"
Cohesion: 0.22
Nodes (9): items, title, type, type, alternatives, references, items, title (+1 more)

### Community 59 - "FindingStatus"
Cohesion: 0.22
Nodes (9): FindingStatus, description, enum, title, type, CONFIRMED, POSSIBLE, PROBABLE (+1 more)

### Community 60 - "enum"
Cohesion: 0.25
Nodes (8): athena, aws_glue, databricks, generic, iceberg, spark, trino, enum

### Community 62 - "properties"
Cohesion: 0.29
Nodes (7): title, type, properties, capability_id, version, title, type

### Community 63 - "ds-0004.md"
Cohesion: 0.33
Nodes (5): Acceptance Criteria, Constraints, Context, Grill Gate, Review Notes

### Community 64 - "ds-0005.implement.claude.md"
Cohesion: 0.40
Nodes (4): Acceptance Criteria, Constraints, Context, Review Notes

### Community 65 - "Review — ds-0005 Analyzer protocol + Spark/Glue log analyzer"
Cohesion: 0.40
Nodes (4): Acceptance criteria check, Findings / notes, Review — ds-0005 Analyzer protocol + Spark/Glue log analyzer, Verdict

### Community 66 - "Platform"
Cohesion: 0.40
Nodes (5): $defs, Platform, description, title, type

### Community 67 - "supported_platforms"
Cohesion: 0.40
Nodes (5): $ref, supported_platforms, items, title, type

### Community 68 - "$defs"
Cohesion: 0.40
Nodes (5): $defs, FindingCategory, description, title, type

### Community 69 - "findings"
Cohesion: 0.40
Nodes (5): items, title, type, $ref, findings

### Community 70 - "limitations"
Cohesion: 0.50
Nodes (4): items, title, type, limitations

### Community 71 - "required_permissions"
Cohesion: 0.50
Nodes (4): required_permissions, items, title, type

### Community 72 - "created_at"
Cohesion: 0.50
Nodes (4): format, title, type, created_at

### Community 73 - "evidence_ids"
Cohesion: 0.50
Nodes (4): items, title, type, evidence_ids

### Community 74 - "explanation"
Cohesion: 0.50
Nodes (4): minLength, title, type, explanation

### Community 75 - "limitations"
Cohesion: 0.50
Nodes (4): items, title, type, limitations

### Community 76 - "recommendations"
Cohesion: 0.50
Nodes (4): recommendations, items, title, type

### Community 77 - "summary"
Cohesion: 0.50
Nodes (4): summary, default, title, type

### Community 78 - "validation_steps"
Cohesion: 0.50
Nodes (4): validation_steps, items, title, type

### Community 79 - "Platform"
Cohesion: 0.50
Nodes (4): Platform, description, title, type

### Community 80 - ".validate_input"
Cohesion: 0.50
Nodes (3): DiagnosticRequest, InputFile, Reject requests the analyzer cannot serve. Pure validation, no IO.

## Knowledge Gaps
- **587 isolated node(s):** `Context`, `Acceptance Criteria`, `Constraints`, `Review Notes`, `Acceptance criteria check` (+582 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ConfigurationError` connect `load_config` to `SentinelError`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Why does `InputValidationError` connect `SentinelError` to `.validate_input`, `read_input_file`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `load_config()` (e.g. with `SentinelConfig` and `ConfigurationError`) actually correct?**
  _`load_config()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `read_input_file()` (e.g. with `InputValidationError` and `.test_allow_binary_decodes_with_replacement()`) actually correct?**
  _`read_input_file()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `SparkGlueLogAnalyzer` (e.g. with `AnalysisResult` and `LogPattern`) actually correct?**
  _`SparkGlueLogAnalyzer` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Context`, `Acceptance Criteria`, `Constraints` to the rest of the system?**
  _587 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `enum` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._