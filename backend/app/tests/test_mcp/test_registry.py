"""Tests for MCP registry."""

from __future__ import annotations

import pytest

from app.mcp.registry import (
    MCPRegistry,
    MCPServerConfig,
    get_mcp_registry,
)


class TestMCPServerConfig:
    def test_http_config(self):
        config = MCPServerConfig(
            name="test",
            transport_type="http",
            url="http://localhost:3000",
        )
        assert config.transport_type == "http"
        assert config.url == "http://localhost:3000"

    def test_stdio_config(self):
        config = MCPServerConfig(
            name="local",
            transport_type="stdio",
            command="python",
            args=["-m", "mcp_server"],
        )
        assert config.command == "python"
        assert config.args == ["-m", "mcp_server"]


class TestMCPRegistry:
    def test_register_and_list(self):
        registry = MCPRegistry()
        config = MCPServerConfig(
            name="test_server",
            transport_type="http",
            url="http://localhost:3000",
            auto_connect=False,
        )
        registry.register(config)
        assert "test_server" in registry.list_servers()

    def test_get_client(self):
        registry = MCPRegistry()
        config = MCPServerConfig(
            name="test_server",
            transport_type="http",
            url="http://localhost:3000",
            auto_connect=False,
        )
        registry.register(config)
        client = registry.get_client("test_server")
        assert client is not None
        assert client.name == "test_server"

    def test_unregister(self):
        registry = MCPRegistry()
        config = MCPServerConfig(
            name="test_server",
            transport_type="http",
            url="http://localhost:3000",
            auto_connect=False,
        )
        registry.register(config)
        registry.unregister("test_server")
        assert "test_server" not in registry.list_servers()

    def test_unknown_transport_raises(self):
        registry = MCPRegistry()
        config = MCPServerConfig(
            name="test",
            transport_type="unknown",
        )
        with pytest.raises(ValueError, match="Unknown transport type"):
            registry.register(config)

    @pytest.mark.asyncio
    async def test_connect_server_not_registered(self):
        registry = MCPRegistry()
        with pytest.raises(KeyError, match="not registered"):
            await registry.connect_server("nonexistent")

    @pytest.mark.asyncio
    async def test_call_tool_not_registered(self):
        registry = MCPRegistry()
        with pytest.raises(KeyError, match="not registered"):
            await registry.call_tool("nonexistent", "tool")


class TestGlobalRegistry:
    def test_get_mcp_registry_singleton(self):
        r1 = get_mcp_registry()
        r2 = get_mcp_registry()
        assert r1 is r2
