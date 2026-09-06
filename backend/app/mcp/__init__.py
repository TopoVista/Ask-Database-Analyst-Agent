"""MCP (Model Context Protocol) integration package.

Provides a client for connecting to MCP servers and a registry for
managing MCP server lifecycle. MCP allows the system to connect to
external data sources and tools through a standardized protocol.
"""

from app.mcp.client import MCPClient, MCPTool
from app.mcp.registry import MCPRegistry, get_mcp_registry

__all__ = [
    "MCPClient",
    "MCPTool",
    "MCPRegistry",
    "get_mcp_registry",
]
