"""Unit tests for ToolRouter's keyword-based routing heuristic and
project_id injection."""
from unittest.mock import AsyncMock

from src.core.tool_router import SPRINT_STATUS_TOOL_NAMES, ToolRouter


def test_requires_tools_true_for_sprint_question():
    """A question containing "sprint" should require the tool chain."""
    router = ToolRouter(mcp_client=AsyncMock(), project_id="proj-123")
    assert router.requires_tools("How is the current sprint going?") is True


def test_requires_tools_false_for_unrelated_question():
    """A question with no sprint-related keywords should not require tools."""
    router = ToolRouter(mcp_client=AsyncMock(), project_id="proj-123")
    assert router.requires_tools("What is the refund policy?") is False


def test_get_tool_chain_includes_project_id_on_every_call():
    """Every tool in the chain should have project_id in its arguments —
    confirmed necessary via a live curl test against Umaku's MCP server,
    which rejected sprints_get_active without it."""
    router = ToolRouter(mcp_client=AsyncMock(), project_id="proj-123")
    chain = router.get_tool_chain("how's the team doing this sprint")

    assert [tool_name for tool_name, _ in chain] == list(SPRINT_STATUS_TOOL_NAMES)
    for _, arguments in chain:
        assert arguments["project_id"] == "proj-123"


def test_get_tool_chain_empty_for_unrelated_question():
    """A non-sprint question should return an empty tool chain."""
    router = ToolRouter(mcp_client=AsyncMock(), project_id="proj-123")
    assert router.get_tool_chain("What is the refund policy?") == []
