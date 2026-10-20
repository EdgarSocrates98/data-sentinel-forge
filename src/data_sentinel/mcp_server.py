"""MCP stdio server (ds-0053, §5.3-§5.5).

Exposes the same registered tools as the CLI over the official `mcp`
SDK (extra `mcp`). Stdio transport only — no remote transport this
cycle. Independent install: works without Forge/Doctor/AWS.

Validate real launch: ``data-sentinel mcp serve`` or
``python -m data_sentinel.mcp_server``.
"""

from __future__ import annotations

import json
from typing import Any

from data_sentinel.core.contracts.agent import ToolInvocation
from data_sentinel.tools import build_default_registry, execute_tool


def create_server(registry: Any = None) -> Any:
    """Build an MCPServer exposing every registered tool."""
    from mcp.server.mcpserver import MCPServer

    reg = registry or build_default_registry()
    server = MCPServer("data-sentinel")

    def _make(tool_id: str) -> Any:
        async def _handler(file: str = "", adapter: str = "",
                           target: str = "", baseline_file: str = "",
                           current_file: str = "") -> str:
            inp = {k: v for k, v in {
                "file": file, "adapter": adapter, "target": target,
                "baseline_file": baseline_file,
                "current_file": current_file}.items() if v}
            res = execute_tool(
                ToolInvocation(invocation_id=f"mcp-{tool_id}",
                               tool_id=tool_id, input=inp))
            payload = res.output if res.ok else {"error": res.error}
            return json.dumps(payload, ensure_ascii=False, default=str)
        return _handler

    for desc in reg.list_tools():
        server.add_tool(
            _make(desc.tool_id), name=desc.tool_id,
            description=desc.description or desc.name)

    return server


def serve() -> None:
    """Run the stdio server (blocking)."""
    create_server().run(transport="stdio")


def main() -> None:  # pragma: no cover
    serve()


if __name__ == "__main__":  # pragma: no cover
    main()
