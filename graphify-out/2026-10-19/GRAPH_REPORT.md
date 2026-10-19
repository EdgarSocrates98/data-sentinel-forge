# Graph Report - data-sentinel-forge  (2026-10-19)

## Corpus Check
- 136 files · ~30,489 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1313 nodes · 1708 edges · 87 communities (82 shown, 5 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 95 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d8725826`
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
- type
- properties
- SentinelError
- test_contracts.py
- Environment
- entities.py
- ResourceContext.schema.json
- contracts/__init__.py
- load_config
- CapabilityManifest.schema.json
- Environment.schema.json
- RequestConstraints.schema.json
- ArtifactReference.schema.json
- description
- AccessMetadata.schema.json
- allowed_roots
- $defs
- DiagnosticRequest
- ds-0003.implement.claude.md
- Review — ds-0003 Configuration system
- Review — ds-0001 Repository foundation and toolchain
- ds-0001.md
- sql_analyzer.py
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
- SentinelStore
- Analyzer
- exceptions/__init__.py
- ArtifactReference
- SqlStaticAnalyzer
- DiagnosticReport.schema.json
- alternatives
- ds-0006.md
- enum
- TestValidation
- properties
- ds-0004.md
- ds-0005.implement.claude.md
- Review — ds-0005 Analyzer protocol + Spark/Glue log analyzer
- Platform
- supported_platforms
- ds-0007.implement.claude.md
- findings
- limitations
- required_permissions
- created_at
- evidence_ids
- Review — ds-0007 Local persistence
- type
- RequestConstraints
- summary
- validation_steps
- references
- AnalysisResult
- ds-0005.md
- ds-0006.implement.claude.md
- Review — ds-0006 SQL static analyzer
- schema_version
- CapabilityManifest
- TestEnums

## God Nodes (most connected - your core abstractions)
1. `load_config()` - 25 edges
2. `SentinelStore` - 24 edges
3. `Analyzer` - 23 edges
4. `ContractModel` - 21 edges
5. `read_input_file()` - 18 edges
6. `safe_resolve()` - 15 edges
7. `request_for()` - 15 edges
8. `enum` - 15 edges
9. `enum` - 15 edges
10. `SparkGlueLogAnalyzer` - 14 edges

## Surprising Connections (you probably didn't know these)
- `TestValidationAndRegistry` --uses--> `AnalyzerRegistry`  [INFERRED]
  tests/unit/test_log_analyzer.py → src/data_sentinel/analyzers/registry.py
- `inputs_for()` --calls--> `read_input_file()`  [INFERRED]
  tests/unit/test_log_analyzer.py → src/data_sentinel/core/security/paths.py
- `inputs_for()` --calls--> `read_input_file()`  [INFERRED]
  tests/unit/test_sql_analyzer.py → src/data_sentinel/core/security/paths.py
- `sample_report()` --calls--> `DiagnosticReport`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py
- `sample_request()` --calls--> `DiagnosticRequest`  [EXTRACTED]
  tests/unit/test_contracts.py → src/data_sentinel/core/contracts/entities.py

## Import Cycles
- None detected.

## Communities (87 total, 5 thin omitted)

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
Cohesion: 0.14
Nodes (14): $ref, minLength, title, type, title, type, properties, category (+6 more)

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
Cohesion: 0.20
Nodes (10): anyOf, default, properties, environment, report_id, request_id, title, type (+2 more)

### Community 10 - "properties"
Cohesion: 0.06
Nodes (33): anyOf, default, format, title, type, maximum, minimum, title (+25 more)

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
Cohesion: 0.25
Nodes (6): Exception, AnalyzerError, Any, An analyzer failed to complete its deterministic pass., Base error carrying a stable code, a message, and optional details., SentinelError

### Community 15 - "test_contracts.py"
Cohesion: 0.11
Nodes (17): Finding, export_schemas(), Path, Export JSON Schemas for the public contracts into schemas/. Usage: uv run…, parametrize, Path, Contract tests: exported JSON Schemas validate serialized examples., test_example_validates_against_schema() (+9 more)

### Community 16 - "Environment"
Cohesion: 0.08
Nodes (25): type, additionalProperties, title, type, Environment, additionalProperties, title, type (+17 more)

### Community 17 - "entities.py"
Cohesion: 0.14
Nodes (21): datetime, _ensure_utc(), Finding, Data Sentinel public domain entities (§4 contracts). Every model serializes to…, An evidence-backed diagnostic conclusion (§4)., AnalysisMode, EvidenceProvenance, ExecutionStatus (+13 more)

### Community 18 - "ResourceContext.schema.json"
Cohesion: 0.08
Nodes (23): additionalProperties, type, description, additionalProperties, title, type, anyOf, default (+15 more)

### Community 19 - "contracts/__init__.py"
Cohesion: 0.13
Nodes (19): AccessMetadata, ArtifactReference, ContractModel, DiagnosticReport, Environment, Evidence, ExecutionContext, Limits the caller imposes on the analysis. (+11 more)

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

### Community 25 - "description"
Cohesion: 0.22
Nodes (9): properties, anyOf, default, title, description, uri, minLength, title (+1 more)

### Community 26 - "AccessMetadata.schema.json"
Cohesion: 0.13
Nodes (14): anyOf, default, title, anyOf, default, title, additionalProperties, description (+6 more)

### Community 27 - "allowed_roots"
Cohesion: 0.20
Nodes (10): items, title, type, type, allowed_roots, timeout_seconds, properties, anyOf (+2 more)

### Community 28 - "$defs"
Cohesion: 0.22
Nodes (9): description, title, type, $defs, AnalysisMode, SourceType, description, title (+1 more)

### Community 29 - "DiagnosticRequest"
Cohesion: 0.20
Nodes (10): CapabilityManifest, DiagnosticRequest, ExecutionMetadata, OptimizationRecommendation, Input describing what should be analyzed and how (§4)., A proposed change with rationale, risk and rollback (§4)., Metadata about the job run the artifacts came from (§4)., Declared capabilities and limitations of an analyzer/component (§4). (+2 more)

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

### Community 34 - "sql_analyzer.py"
Cohesion: 0.26
Nodes (15): Expr, SqlHit, _count_distinct(), _implicit_joins(), _is_trivial_on(), _large_in_lists(), _nonsargable_predicates(), _order_without_limit() (+7 more)

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
Nodes (31): fixture, MonkeyPatch, parametrize, InputValidationError, User-supplied input is invalid or unsafe to process., Security primitives: path guard, file-input guard, sanitization, redaction., InputFile, _looks_binary() (+23 more)

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
Cohesion: 0.17
Nodes (12): Platform, athena, aws_glue, databricks, generic, iceberg, spark, trino (+4 more)

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
Cohesion: 0.08
Nodes (24): FindingStatus, Path, Platform, DiagnosticRequest, InputFile, Reject requests the analyzer cannot serve. Pure validation, no IO., Run the deterministic pass. Never fabricates findings., inputs_for() (+16 more)

### Community 51 - "max_file_bytes"
Cohesion: 0.50
Nodes (4): anyOf, default, title, max_file_bytes

### Community 52 - "SentinelStore"
Cohesion: 0.07
Nodes (32): Connection, PersistenceError, Local persistence (storage, migrations) failed., Local persistence: SQLite store + migrations., apply_migrations(), _migration_files(), Path, Append-only, transactional SQL migrations (stdlib sqlite3 only). (+24 more)

### Community 53 - "Analyzer"
Cohesion: 0.11
Nodes (10): ABC, CapabilityManifest, Analyzer, SourceType, Analyzer protocol: the stable interface every analyzer implements (§01.3)., Deterministic, local, read-only analyzer contract., AnalyzerRegistry, SourceType (+2 more)

### Community 54 - "exceptions/__init__.py"
Cohesion: 0.20
Nodes (9): Self, Any, ContractValidationError, PathViolationError, Domain exceptions with structured error information., A public contract failed to parse or validate., A request violated a security guard (paths, secrets, limits)., A file path resolved outside the allowed roots. (+1 more)

### Community 55 - "ArtifactReference"
Cohesion: 0.29
Nodes (7): additionalProperties, description, required, title, type, ArtifactReference, uri

### Community 56 - "SqlStaticAnalyzer"
Cohesion: 0.20
Nodes (4): Analyzer package: protocol, registry, and built-in analyzers., SourceType, Pattern-based static inspection of SQL text. No execution, no plan., SqlStaticAnalyzer

### Community 57 - "DiagnosticReport.schema.json"
Cohesion: 0.22
Nodes (8): created_at, request_id, additionalProperties, description, required, $schema, title, type

### Community 58 - "alternatives"
Cohesion: 0.50
Nodes (4): items, title, type, alternatives

### Community 59 - "ds-0006.md"
Cohesion: 0.33
Nodes (5): Acceptance Criteria, Constraints, Context, Grill Gate, Review Notes

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

### Community 68 - "ds-0007.implement.claude.md"
Cohesion: 0.40
Nodes (4): Acceptance Criteria, Constraints, Context, Review Notes

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

### Community 74 - "Review — ds-0007 Local persistence"
Cohesion: 0.40
Nodes (4): Acceptance criteria check, Findings / notes, Review — ds-0007 Local persistence, Verdict

### Community 75 - "type"
Cohesion: 0.22
Nodes (9): type, items, title, type, limitations, recommendations, items, title (+1 more)

### Community 76 - "RequestConstraints"
Cohesion: 0.40
Nodes (5): RequestConstraints, additionalProperties, description, title, type

### Community 77 - "summary"
Cohesion: 0.50
Nodes (4): summary, default, title, type

### Community 78 - "validation_steps"
Cohesion: 0.50
Nodes (4): validation_steps, items, title, type

### Community 79 - "references"
Cohesion: 0.50
Nodes (4): references, items, title, type

### Community 80 - "AnalysisResult"
Cohesion: 0.22
Nodes (8): AnalysisResult, Internal output of one analyzer pass over one request. Not a wire contract —…, DiagnosticRequest, InputFile, _dialect_for(), _line_of_fragment(), DiagnosticRequest, InputFile

### Community 81 - "ds-0005.md"
Cohesion: 0.33
Nodes (5): Acceptance Criteria, Constraints, Context, Grill Gate, Review Notes

### Community 82 - "ds-0006.implement.claude.md"
Cohesion: 0.40
Nodes (4): Acceptance Criteria, Constraints, Context, Review Notes

### Community 83 - "Review — ds-0006 SQL static analyzer"
Cohesion: 0.40
Nodes (4): Acceptance criteria check, Findings / notes, Review — ds-0006 SQL static analyzer, Verdict

### Community 84 - "schema_version"
Cohesion: 0.50
Nodes (4): schema_version, default, title, type

## Knowledge Gaps
- **612 isolated node(s):** `Context`, `Acceptance Criteria`, `Constraints`, `Review Notes`, `Acceptance criteria check` (+607 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `read_input_file()` connect `read_input_file` to `.analyze`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `ConfigurationError` connect `load_config` to `exceptions/__init__.py`, `SentinelError`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `load_config()` (e.g. with `SentinelConfig` and `ConfigurationError`) actually correct?**
  _`load_config()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `SentinelStore` (e.g. with `.test_corrupted_db_raises_domain_error()` and `.test_readonly_dir_raises_domain_error()`) actually correct?**
  _`SentinelStore` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `read_input_file()` (e.g. with `InputValidationError` and `.test_allow_binary_decodes_with_replacement()`) actually correct?**
  _`read_input_file()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Context`, `Acceptance Criteria`, `Constraints` to the rest of the system?**
  _612 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `enum` be split into smaller, more focused modules?**
  _Cohesion score 0.0425531914893617 - nodes in this community are weakly interconnected._