"""Umaku MCP client — read-only tool calls used in Moment 5.

Connects to Umaku's hosted MCP server (https://mcp.umaku.ai/mcp) using a
personal access token, via the MCP Python SDK's streamable HTTP
transport. Only the four read-only tools needed for the demo are
exposed here deliberately, even though Umaku's MCP server supports
writes — see docs/architecture_plan.md for the read-only scope decision.

A fresh session is opened per tool call rather than held open across
calls. This is slightly less efficient than a persistent session, but
much simpler to reason about for a demo doing a handful of calls per
question, and avoids managing reconnect logic if a session drops
between Moment 5 and a later dry run.

NOTE on the MCP SDK version: as of mcp>=2.0, the transport function is
`streamable_http_client` (renamed from `streamablehttp_client` in 1.x —
confirmed via a live install), and it no longer accepts a `headers`
kwarg directly. Auth headers must instead be set on an explicit
`httpx2.AsyncClient` (mcp 2.0's own HTTP client dependency — a separate
package from `httpx`, not a typo) passed in as `http_client=`.
"""
import json

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.infrastructure.mcp.base import BaseMCPClient
from utils.logger import get_logger

logger = get_logger()

# The four tools this demo is scoped to use, all read-only.
READ_ONLY_TOOLS = (
    "sprints_get_active",
    "kanban_get_board",
    "projects_get_dashboard",
    "performance_assessments_by_project",
)

# Umaku's own health_check tool, used by our health_check() method —
# separate from READ_ONLY_TOOLS since it's not part of the demo's
# scripted tool chain, just a connectivity check.
HEALTH_CHECK_TOOL = "health_check"


def _extract_tool_result(
    call_result,
) -> dict:
    """Extract a plain dict from an MCP CallToolResult.

    Prefers `structured_content` (already a parsed dict, when the server
    provides it) over parsing the text content block, since not every
    MCP server returns machine-readable text.

    NOTE: mcp 2.0's CallToolResult uses snake_case Python attributes —
    `is_error` and `structured_content` — not the camelCase
    `isError`/`structuredContent` seen in the raw JSON-RPC wire format
    (that's just standard JSON-RPC/MCP protocol casing, unrelated to
    how the Python SDK's Pydantic model exposes the same data).
    Confirmed against mcp 2.0's actual CallToolResult.model_fields, not
    assumed — an earlier version of this code used the camelCase names,
    which raised AttributeError on every real call.

    Args:
        call_result: The raw mcp.types.CallToolResult from the SDK.

    Returns:
        A plain dict representing the tool's result.

    Raises:
        ValueError: If the tool call itself reported an error, or if no
            usable result content could be extracted.
    """
    if call_result.is_error:
        error_text = _first_text_block(call_result)
        raise ValueError(f"Umaku tool call returned an error: {error_text}")

    if call_result.structured_content is not None:
        return call_result.structured_content

    text = _first_text_block(call_result)
    if text is None:
        raise ValueError("Umaku tool call returned no usable content")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some tools may return plain text rather than JSON — wrap it so
        # callers always get a dict, matching MCPClientInterface's contract.
        return {"text": text}


def _first_text_block(
    call_result,
) -> str | None:
    """Return the text of the first TextContent block in a tool result, if any.

    Args:
        call_result: The raw mcp.types.CallToolResult from the SDK.
    """
    for block in call_result.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return None


class UmakuMCPClient(BaseMCPClient):
    """MCP client for Umaku's hosted server, restricted to read-only tools."""

    def __init__(
        self,
        mcp_url: str,
        token: str,
    ) -> None:
        """Initialize the client's connection parameters.

        Args:
            mcp_url: The URL of Umaku's hosted MCP server.
            token: The personal access token generated from Umaku's
                Account Settings -> MCP page.
        """
        self._mcp_url = mcp_url
        self._token = token

    async def list_tools(
        self,
    ) -> list[str]:
        """Return the demo's fixed read-only tool allow-list.

        Deliberately returns the curated allow-list rather than querying
        the server's full tool catalog, since this client should never
        expose write tools regardless of what Umaku's server offers.
        """
        return list(READ_ONLY_TOOLS)

    async def _do_call_tool(
        self,
        tool_name: str,
        arguments: dict,
    ) -> dict:
        """Open a session, invoke a read-only Umaku MCP tool, and return its result.

        Args:
            tool_name: The name of the tool to call. Must be one of
                READ_ONLY_TOOLS (or HEALTH_CHECK_TOOL, used internally
                by health_check()).
            arguments: The arguments to pass to the tool.

        Raises:
            ValueError: If `tool_name` is not in the read-only allow-list.
        """
        if tool_name not in READ_ONLY_TOOLS and tool_name != HEALTH_CHECK_TOOL:
            raise ValueError(
                f"Tool '{tool_name}' is not in the demo's read-only allow-list"
            )

        # Auth is via the `x-umaku-token` HTTP header — confirmed against
        # docs.umaku.ai. The MCP server forwards it as a Bearer token to
        # Umaku's backend internally, but that's not our client's concern.
        # As of mcp>=2.0, streamable_http_client no longer takes headers
        # directly — they're set on the httpx2.AsyncClient passed as
        # http_client instead (see module docstring).
        auth_client = httpx2.AsyncClient(
            headers={"x-umaku-token": self._token},
        )
        # NOTE: mcp 2.0's streamable_http_client yields a 2-tuple
        # (read_stream, write_stream) — confirmed against its docstring
        # and TransportStreams type. This differs from the old 1.x
        # streamablehttp_client, which yielded a 3-tuple including a
        # get_session_id callable that no longer exists in 2.0. An
        # earlier version of this code kept the 3-value unpack from the
        # 1.x API, which raised "not enough values to unpack" on every
        # call — caught via a live run, not assumed.
        async with streamable_http_client(
            self._mcp_url,
            http_client=auth_client,
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return _extract_tool_result(result)

    async def health_check(
        self,
    ) -> bool:
        """Return True if the Umaku MCP server is reachable and the token is valid."""
        try:
            await self._do_call_tool(HEALTH_CHECK_TOOL, {})
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Umaku health check failed: {exc}")
            return False
