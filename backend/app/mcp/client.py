"""MCP client for connecting to Model Context Protocol servers.

Provides a lightweight client that can discover and invoke tools
exposed by MCP servers. Supports both HTTP/SSE and stdio transports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class MCPTool:
    """A tool exposed by an MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    server_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "server_name": self.server_name,
        }


@runtime_checkable
class MCPTransport(Protocol):
    """Transport layer for MCP communication."""

    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        ...

    async def disconnect(self) -> None:
        """Close the connection."""
        ...

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the server."""
        ...

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a tool on the server."""
        ...


class HTTPMCPTransport:
    """HTTP/SSE transport for MCP servers."""

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url.rstrip("/")
        self.headers = headers or {}
        self._session = None

    async def connect(self) -> None:
        import httpx

        self._session = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    async def disconnect(self) -> None:
        if self._session:
            await self._session.aclose()
            self._session = None

    async def list_tools(self) -> list[dict[str, Any]]:
        if not self._session:
            await self.connect()
        response = await self._session.get(f"{self.url}/tools")
        response.raise_for_status()
        return response.json().get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if not self._session:
            await self.connect()
        response = await self._session.post(
            f"{self.url}/tools/{tool_name}/call",
            json=arguments,
        )
        response.raise_for_status()
        return response.json()


class StdioMCPTransport:
    """Stdio transport for local MCP servers (spawned as subprocess)."""

    def __init__(self, command: str, args: list[str] | None = None, env: dict[str, str] | None = None) -> None:
        self.command = command
        self.args = args or []
        self.env = env
        self._process = None
        self._connected = False

    async def connect(self) -> None:
        import asyncio

        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env,
        )
        self._connected = True

    async def disconnect(self) -> None:
        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None
        self._connected = False

    async def _send_request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a JSON-RPC request over stdio."""
        import json

        request = {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex,
            "method": method,
            "params": params or {},
        }
        request_bytes = (json.dumps(request) + "\n").encode()
        self._process.stdin.write(request_bytes)
        await self._process.stdin.drain()

        response_line = await self._process.stdout.readline()
        return json.loads(response_line.decode())

    async def list_tools(self) -> list[dict[str, Any]]:
        if not self._connected:
            await self.connect()
        result = await self._send_request("tools/list")
        return result.get("result", {}).get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if not self._connected:
            await self.connect()
        result = await self._send_request("tools/call", {"name": tool_name, "arguments": arguments})
        return result.get("result", {})


class MCPClient:
    """High-level MCP client that manages a transport and exposes tools."""

    def __init__(self, name: str, transport: MCPTransport) -> None:
        self.name = name
        self.transport = transport
        self._tools: dict[str, MCPTool] = {}
        self._connected = False

    async def connect(self) -> None:
        """Connect to the MCP server and discover tools."""
        await self.transport.connect()
        raw_tools = await self.transport.list_tools()
        for raw in raw_tools:
            tool = MCPTool(
                name=raw.get("name", ""),
                description=raw.get("description", ""),
                input_schema=raw.get("inputSchema", raw.get("input_schema", {})),
                server_name=self.name,
            )
            self._tools[tool.name] = tool
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        await self.transport.disconnect()
        self._connected = False

    async def list_tools(self) -> list[MCPTool]:
        """List all available tools."""
        return list(self._tools.values())

    async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Invoke a tool by name with the given arguments."""
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' not found on MCP server '{self.name}'")
        return await self.transport.call_tool(tool_name, kwargs)

    def get_tool(self, tool_name: str) -> MCPTool | None:
        """Get tool metadata by name."""
        return self._tools.get(tool_name)

    @property
    def is_connected(self) -> bool:
        return self._connected
