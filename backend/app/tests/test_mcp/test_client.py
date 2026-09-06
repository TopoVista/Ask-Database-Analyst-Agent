"""Tests for MCP client."""

from __future__ import annotations

import pytest

from app.mcp.client import (
    HTTPMCPTransport,
    MCPClient,
    MCPTool,
    MCPTransport,
)


class FakeTransport:
    """Fake transport for testing."""

    def __init__(self, tools: list[dict] | None = None, call_result: Any = None) -> None:
        self._tools = tools or []
        self._call_result = call_result or {"result": "ok"}
        self.connected = False
        self.disconnected = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.disconnected = True

    async def list_tools(self) -> list[dict]:
        return self._tools

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        self.last_call = (tool_name, arguments)
        return self._call_result


class TestMCPTool:
    def test_to_dict(self):
        tool = MCPTool(name="test", description="A test tool", server_name="server1")
        d = tool.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "A test tool"
        assert d["server_name"] == "server1"


class TestMCPClient:
    @pytest.mark.asyncio
    async def test_connect_discovers_tools(self):
        fake = FakeTransport(tools=[
            {"name": "query", "description": "Run a query"},
            {"name": "schema", "description": "Get schema"},
        ])
        client = MCPClient("test_server", fake)
        await client.connect()

        assert client.is_connected
        assert fake.connected
        tools = await client.list_tools()
        assert len(tools) == 2
        assert tools[0].name == "query"

    @pytest.mark.asyncio
    async def test_call_tool_forwards_to_transport(self):
        fake = FakeTransport(
            tools=[{"name": "query", "description": "Run"}],
            call_result={"rows": [{"id": 1}]},
        )
        client = MCPClient("test_server", fake)
        await client.connect()

        result = await client.call_tool("query", sql="SELECT 1")
        assert result == {"rows": [{"id": 1}]}
        assert fake.last_call == ("query", {"sql": "SELECT 1"})

    @pytest.mark.asyncio
    async def test_call_unknown_tool_raises(self):
        fake = FakeTransport(tools=[])
        client = MCPClient("test_server", fake)
        await client.connect()

        with pytest.raises(KeyError, match="not found"):
            await client.call_tool("nonexistent")

    @pytest.mark.asyncio
    async def test_get_tool_returns_metadata(self):
        fake = FakeTransport(tools=[{"name": "query", "description": "Run"}])
        client = MCPClient("test_server", fake)
        await client.connect()

        tool = client.get_tool("query")
        assert tool is not None
        assert tool.name == "query"

    @pytest.mark.asyncio
    async def test_disconnect(self):
        fake = FakeTransport()
        client = MCPClient("test_server", fake)
        await client.connect()
        await client.disconnect()

        assert not client.is_connected
        assert fake.disconnected

    def test_http_transport_init(self):
        transport = HTTPMCPTransport("http://localhost:3000", headers={"Auth": "Bearer token"})
        assert transport.url == "http://localhost:3000"
        assert transport.headers == {"Auth": "Bearer token"}


class TestMCPToolDataclass:
    def test_default_values(self):
        tool = MCPTool(name="t", description="d")
        assert tool.input_schema == {}
        assert tool.server_name == ""
