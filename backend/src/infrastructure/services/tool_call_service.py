"""Wraps an MCPClientInterface with cross-cutting concerns.

Note: BaseMCPClient already provides consistent timing/error-shaping for
individual calls. This service is the place for chain-level concerns —
e.g. short-circuiting the remaining calls in a chain if an early call
fails, which is a policy decision that shouldn't live in the client
itself.
"""
from src.domain.entities.tool_call import ToolCallResult, ToolCallStatus
from src.domain.interfaces.mcp_client import MCPClientInterface


class ToolCallService(MCPClientInterface):
    """Chain-level orchestration decorator around a concrete MCPClientInterface."""

    def __init__(
        self,
        mcp_client: MCPClientInterface,
    ) -> None:
        """Initialize the service.

        Args:
            mcp_client: The underlying MCP client to delegate to.
        """
        self._mcp_client = mcp_client

    async def list_tools(
        self,
    ) -> list[str]:
        """Delegate to the underlying client's tool listing."""
        return await self._mcp_client.list_tools()

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict,
    ) -> ToolCallResult:
        """Delegate a single tool call to the underlying client.

        Args:
            tool_name: The name of the tool to call.
            arguments: The arguments to pass to the tool.
        """
        return await self._mcp_client.call_tool(tool_name, arguments)

    async def call_chain(
        self,
        calls: list[tuple[str, dict]],
        stop_on_failure: bool = True,
    ) -> list[ToolCallResult]:
        """Run an ordered chain of tool calls.

        Args:
            calls: The (tool_name, arguments) pairs to call, in order.
            stop_on_failure: Whether to stop the chain as soon as one
                call fails, rather than continuing through the rest.

        Returns:
            The results of each call attempted, in order.
        """
        results: list[ToolCallResult] = []
        for tool_name, arguments in calls:
            result = await self._mcp_client.call_tool(tool_name, arguments)
            results.append(result)
            if stop_on_failure and result.status == ToolCallStatus.FAILURE:
                break
        return results

    async def health_check(
        self,
    ) -> bool:
        """Delegate the health check to the underlying client."""
        return await self._mcp_client.health_check()
