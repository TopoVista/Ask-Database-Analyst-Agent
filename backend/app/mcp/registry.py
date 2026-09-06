"""MCP Registry for managing server lifecycle.

Maintains a registry of MCP server configurations and their clients,
allowing dynamic registration, discovery, and cleanup of MCP servers.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.mcp.client import MCPClient, MCPTransport


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    description: str = ""
    transport_type: str = "http"  # "http" or "stdio"
    # For HTTP transport
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    # For stdio transport
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    # Auto-connect on registration
    auto_connect: bool = True
    # Read-only mode (no write operations allowed)
    read_only: bool = True


class MCPRegistry:
    """Registry for MCP servers and their clients."""

    def __init__(self) -> None:
        self._configs: dict[str, MCPServerConfig] = {}
        self._clients: dict[str, MCPClient] = {}

    def register(self, config: MCPServerConfig) -> MCPClient:
        """Register an MCP server and return a client."""
        if config.name in self._configs:
            raise ValueError(f"MCP server '{config.name}' is already registered")

        transport = self._create_transport(config)
        client = MCPClient(name=config.name, transport=transport)

        self._configs[config.name] = config
        self._clients[config.name] = client

        return client

    def unregister(self, name: str) -> bool:
        """Unregister an MCP server and disconnect its client."""
        client = self._clients.pop(name, None)
        if client is not None and client.is_connected:
            asyncio.create_task(client.disconnect())
        return self._configs.pop(name, None) is not None

    def get_client(self, name: str) -> MCPClient | None:
        """Get the client for a registered server."""
        return self._clients.get(name)

    def get_config(self, name: str) -> MCPServerConfig | None:
        """Get the configuration for a registered server."""
        return self._configs.get(name)

    def list_servers(self) -> list[str]:
        """List all registered server names."""
        return list(self._configs.keys())

    def list_clients(self) -> list[MCPClient]:
        """List all clients."""
        return list(self._clients.values())

    async def connect_all(self) -> None:
        """Connect all registered clients."""
        for client in self._clients.values():
            if not client.is_connected:
                await client.connect()

    async def disconnect_all(self) -> None:
        """Disconnect all clients."""
        for client in self._clients.values():
            if client.is_connected:
                await client.disconnect()

    def _create_transport(self, config: MCPServerConfig) -> MCPTransport:
        """Create a transport from configuration."""
        if config.transport_type == "http":
            from app.mcp.client import HTTPMCPTransport
            return HTTPMCPTransport(url=config.url, headers=config.headers)
        elif config.transport_type == "stdio":
            from app.mcp.client import StdioMCPTransport
            return StdioMCPTransport(
                command=config.command,
                args=config.args,
                env=config.env,
            )
        else:
            raise ValueError(f"Unknown transport type: {config.transport_type}")

    def get_all_tools(self) -> dict[str, list[dict[str, Any]]]:
        """Get all tools from all connected servers."""
        tools: dict[str, list[dict[str, Any]]] = {}
        for name, client in self._clients.items():
            if client.is_connected:
                tools[name] = [t.to_dict() for t in client.list_tools()]
        return tools

    async def connect_server(self, name: str) -> None:
        """Connect to a registered server by name."""
        client = self._clients.get(name)
        if client is None:
            raise KeyError(f"Server '{name}' is not registered")
        await client.connect()

    async def call_tool(self, server_name: str, tool_name: str, **kwargs: Any) -> Any:
        """Call a tool on a registered server."""
        client = self._clients.get(server_name)
        if client is None:
            raise KeyError(f"Server '{server_name}' is not registered")
        return await client.call_tool(tool_name, **kwargs)


# Global registry instance
_global_registry: MCPRegistry | None = None


def get_mcp_registry() -> MCPRegistry:
    """Get or create the global MCP registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = MCPRegistry()
    return _global_registry
