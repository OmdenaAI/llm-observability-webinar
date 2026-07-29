"""Abstract base for MCP client implementations."""
import time
from abc import abstractmethod

from src.domain.entities.tool_call import ToolCallResult, ToolCallStatus
from src.domain.interfaces.mcp_client import MCPClientInterface
from utils.logger import get_logger

logger = get_logger()


def _unwrap_exception(
    exc: BaseException,
) -> BaseException:
    """Recursively unwrap ExceptionGroup/BaseExceptionGroup to the first
    concrete leaf exception.

    The MCP SDK's streamable HTTP transport uses anyio task groups
    internally (a background task handles the server's SSE stream). When
    something inside that background task fails, anyio wraps it in an
    ExceptionGroup with a generic "unhandled errors in a TaskGroup"
    message — logging that message alone hides the actual cause (a
    connection error, auth failure, timeout, etc.). This walks down to
    the real exception so it's visible in logs and in the ToolCallResult.

    Args:
        exc: The exception caught from a failed tool call.

    Returns:
        The first non-group exception found, or `exc` itself if it
        isn't a group (or is an empty one).
    """
    current = exc
    while isinstance(current, (ExceptionGroup, BaseExceptionGroup)) and current.exceptions:
        current = current.exceptions[0]
    return current


class BaseMCPClient(MCPClientInterface):
    """Shared timing/error handling around concrete MCP tool calls.

    Wraps concrete tool calls so every MCP implementation produces a
    consistently-shaped ToolCallResult, whether the call succeeds or
    fails.
    """

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict,
    ) -> ToolCallResult:
        """Time and error-wrap a call to the concrete MCP transport.

        Args:
            tool_name: The name of the tool to call.
            arguments: The arguments to pass to the tool.

        Returns:
            The result of the call, including timing and success/failure
            status. Failures are captured here rather than raised, so
            callers always get a well-formed ToolCallResult.
        """
        start = time.perf_counter()
        try:
            result = await self._do_call_tool(tool_name, arguments)
            latency_ms = (time.perf_counter() - start) * 1000
            return ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                status=ToolCallStatus.SUCCESS,
                latency_ms=latency_ms,
            )
        except Exception as exc:  # noqa: BLE001 — deliberately broad, converted to a domain result
            latency_ms = (time.perf_counter() - start) * 1000
            real_exc = _unwrap_exception(exc)
            error_message = f"{type(real_exc).__name__}: {real_exc}"
            logger.error(f"MCP tool call failed: {tool_name} — {error_message}")
            return ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                status=ToolCallStatus.FAILURE,
                latency_ms=latency_ms,
                error_message=error_message,
            )

    @abstractmethod
    async def _do_call_tool(
        self,
        tool_name: str,
        arguments: dict,
    ) -> dict:
        """Perform the actual tool call against the concrete MCP transport.

        Args:
            tool_name: The name of the tool to call.
            arguments: The arguments to pass to the tool.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_tools(
        self,
    ) -> list[str]:
        """Return the names of tools exposed by the connected server."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(
        self,
    ) -> bool:
        """Return True if the MCP server is reachable and authenticated."""
        raise NotImplementedError
