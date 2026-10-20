"""API/MCP readiness contracts — shapes a future server must honor.

Readiness criteria (checked by tests, not by a running server):
- request validation mirrors DiagnosticRequest rules
- error payloads are structured (code/message/details/request_id)
- MCP tool descriptors are declarative and read-only
"""

from pydantic import BaseModel, Field

from data_sentinel.core.contracts import (
    DiagnosticReport,
    Finding,
    Platform,
    SourceType,
)


class ApiDiagnosticRequest(BaseModel):
    """v1 diagnose request — same required fields as DiagnosticRequest."""

    source_type: SourceType
    platform: Platform
    artifact_references: list[str] = Field(min_length=1)
    runtime_version: str | None = None
    no_persist: bool = True  # API defaults to no persistence


class ApiDiagnosticResponse(BaseModel):
    request_id: str
    report: DiagnosticReport
    findings_count: int


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)
    request_id: str


class ApiCapabilitiesResponse(BaseModel):
    analyzers: list[str]
    version: str


class McpToolDescriptor(BaseModel):
    """Declarative tool shape for a future MCP server — read-only only."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str
    input_schema: dict[str, object] = Field(default_factory=dict)
    read_only: bool = True


MCP_READINESS_TOOLS: tuple[McpToolDescriptor, ...] = (
    McpToolDescriptor(
        name="sentinel_analyze_artifact",
        description="Analisa um artefato local (log/plano/SQL) com evidências.",
        input_schema=ApiDiagnosticRequest.model_json_schema(),
    ),
    McpToolDescriptor(
        name="sentinel_list_capabilities",
        description="Lista analyzers registrados e operações suportadas.",
        input_schema={"type": "object", "properties": {}},
    ),
    McpToolDescriptor(
        name="sentinel_get_finding",
        description="Detalha um finding por ID com evidências sanitizadas.",
        input_schema=Finding.model_json_schema(),
    ),
)
