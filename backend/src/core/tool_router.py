"""Decides which MCP tools (if any) a question requires.

This is intentionally simple/rule-based for the demo — the point being
illustrated live (Moment 5) is that MCP gives tool calls a traceable,
consistent shape, not that the routing logic itself is sophisticated.
A production system would likely let the LLM choose tools via function
calling; this demo uses explicit routing so the four-call chain is
reliable and repeatable on stage.
"""
from src.domain.interfaces.mcp_client import MCPClientInterface

# Tools called for the "sprint + team" question used in Moment 5, in
# order. `project_id` is required by all four — confirmed via a live
# curl test against Umaku's MCP server, which returned a validation
# error for sprints_get_active when called without it:
#   "1 validation error for call[sprints_get_active] / project_id /
#    Missing required argument"
# ToolRouter injects project_id into every call's arguments at request
# time from its configured value — never hardcoded per-tool.
# kanban_get_board additionally needs `sprint_ids`, which
# RAGOrchestrator threads in dynamically from sprints_get_active's
# result (project_id alone isn't enough for that one tool).
SPRINT_STATUS_TOOL_NAMES = (
    "sprints_get_active",
    "kanban_get_board",
    "projects_get_dashboard",
    "performance_assessments_by_project",
)


class ToolRouter:
    """Maps a question to zero or more MCP tool calls, in order."""

    def __init__(
        self,
        mcp_client: MCPClientInterface,
        project_id: str = "",
    ) -> None:
        """Initialize the router.

        Args:
            mcp_client: The MCP client the router will eventually
                delegate calls to (currently unused directly by the
                router itself, but held for parity with other
                components and future LLM-driven routing).
            project_id: The Umaku project ID injected into every tool
                call's arguments — required by every project-scoped
                Umaku tool this demo calls.
        """
        self._mcp_client = mcp_client
        self._project_id = project_id

    def requires_tools(
        self,
        question: str,
    ) -> bool:
        """Return True if the question should trigger an MCP tool chain.

        Very small heuristic — good enough for a fixed demo question set.
        Extend this if additional questions/tool chains are added later.

        Args:
            question: The user's natural-language question.
        """
        sprint_keywords = ("sprint", "team", "kanban", "board", "performance")
        return any(
            keyword in question.lower()
            for keyword in sprint_keywords
        )

    def get_tool_chain(
        self,
        question: str,
    ) -> list[tuple[str, dict]]:
        """Return the ordered tool chain for the given question, if any.

        Args:
            question: The user's natural-language question.

        Returns:
            A list of (tool_name, arguments) pairs to call in order,
            each pre-filled with `project_id`, or an empty list if the
            question requires no tool calls.
        """
        if not self.requires_tools(question):
            return []
        return [
            (tool_name, {"project_id": self._project_id})
            for tool_name in SPRINT_STATUS_TOOL_NAMES
        ]
