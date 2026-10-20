"""API/MCP readiness contracts (Cycle 02 scope: contracts only).

Per the cycle grill decision, a live FastAPI surface and MCP server are
deferred — these versioned contracts define the shape a future server
must honor, and readiness tests guard the contract.
"""

from data_sentinel.api.contracts import (
    ApiCapabilitiesResponse,
    ApiDiagnosticRequest,
    ApiDiagnosticResponse,
    ApiError,
    McpToolDescriptor,
)

__all__ = [
    "ApiCapabilitiesResponse",
    "ApiDiagnosticRequest",
    "ApiDiagnosticResponse",
    "ApiError",
    "McpToolDescriptor",
]
