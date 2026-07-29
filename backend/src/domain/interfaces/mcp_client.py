"""Contract for an MCP client (e.g. Umaku).

Kept generic (not Umaku-specific) so the demo could point at a different
MCP server without changing core/ — only infrastructure/mcp/*.
"""
from abc import ABC, abstractmethod

from src.domain.entities.tool_call import ToolCallResult


class MCPClientInterface(ABC):
    """Abstract contract for listing and calling tools on an MCP server."""

    @abstractmethod
    async def list_tools(
        self,
    ) -> list[str]:
        """Return the names of tools currently exposed by the connected
        MCP server."""
        raise NotImplementedError

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict,
    ) -> ToolCallResult:
        """Invoke a single tool on the connected MCP server.

        Args:
            tool_name: The name of the tool to call (e.g.
                "sprints_get_active").
            arguments: The arguments to pass to the tool.

        Returns:
            The result of the call, including timing and success/failure
            status.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(
        self,
    ) -> bool:
        """Return True if the MCP server is reachable and the configured
        token is valid."""
        raise NotImplementedError
