"""MCP stdio real-launch test (ds-0053): subprocess + real client."""

import pytest

mcp = pytest.importorskip("mcp", reason="extra mcp ausente")


@pytest.mark.anyio
async def test_mcp_stdio_roundtrip() -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command="uv", args=["run", "python", "-m",
                            "data_sentinel.mcp_server"])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        ids = {t.name for t in tools.tools}
        assert "sentinel.sql.analyze" in ids
        assert "sentinel.lineage.ingest" in ids
        res = await session.call_tool(
            "sentinel.lineage.ingest",
            {"file": "tests/fixtures/lineage/marquez-real.jsonl"})
        text = res.content[0].text  # type: ignore[union-attr]
        assert "analytics/customer_events" in text


@pytest.mark.anyio
async def test_mcp_unknown_tool_error_is_data() -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command="uv", args=["run", "python", "-m",
                            "data_sentinel.mcp_server"])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        res = await session.call_tool("sentinel.nope", {})
        assert res.is_error
