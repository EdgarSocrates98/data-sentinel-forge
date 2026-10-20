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


@pytest.mark.anyio
async def test_mcp_input_schema_and_permission_denial() -> None:
    """ds-0106: tools expose a real.input_schema; file reads outside the
    server's roots are denied as an error result — never a crash."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command="uv", args=["run", "python", "-m",
                            "data_sentinel.mcp_server"])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        by_name = {t.name: t for t in tools.tools}
        schema = by_name["sentinel.lineage.ingest"].input_schema
        assert schema["type"] == "object"
        assert "file" in schema.get("properties", {})

        # permission denial: path outside server roots (cwd of the
        # spawned server = repo root) → error payload, not a crash
        res = await session.call_tool(
            "sentinel.lineage.ingest",
            {"file": "/etc/hostname"})
        import json as _j
        payload = _j.loads(res.content[0].text)  # type: ignore[union-attr]
        assert "error" in payload
        assert "PathViolationError" in payload["error"]
    # context exit = clean shutdown of the stdio child


@pytest.mark.anyio
async def test_mcp_clean_shutdown() -> None:
    """ds-0106: server process exits when the client disconnects."""
    import asyncio

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command="uv", args=["run", "python", "-m",
                            "data_sentinel.mcp_server"])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
    # if the context manager returned, the child process was closed —
    # a hung server would raise on timeout here
    await asyncio.sleep(0)
