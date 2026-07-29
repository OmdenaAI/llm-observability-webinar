"""Moment 5 — Traceability: an MCP Tool Call, End to End.

Runs the fixed sprint-status question, which the ToolRouter (inside
RAGOrchestrator) recognizes and expands into the four-call chain against
Umaku: sprints_get_active, kanban_get_board, projects_get_dashboard,
performance_assessments_by_project. All read-only.
"""
from dataclasses import dataclass

from src.core.rag_orchestrator import RAGOrchestrator, RAGResponse
from src.domain.entities.tool_call import ToolCallResult
from src.domain.interfaces.gateway import GatewayInterface

SPRINT_STATUS_QUESTION = "How is the current sprint going, and how's the team doing?"


@dataclass
class TraceabilityScenarioResult:
    """The result of running the traceability scenario.

    Attributes:
        response: The full RAG response, including the MCP tool chain.
    """

    response: RAGResponse

    @property
    def tool_call_count(
        self,
    ) -> int:
        """Return how many MCP tool calls were made to answer the question."""
        return len(self.response.tool_chain.calls) if self.response.tool_chain else 0

    @property
    def all_calls_succeeded(
        self,
    ) -> bool:
        """Return True if every tool call in the chain succeeded."""
        return bool(
            self.response.tool_chain and self.response.tool_chain.all_succeeded
        )

    @property
    def calls(
        self,
    ) -> list[ToolCallResult]:
        """Return the individual per-call results, in call order.

        Exposes the same detail already captured internally (tool name,
        success/failure status, latency, error message per call) so the
        API/UI can show each MCP call individually, rather than only an
        aggregate count and a single success/failure flag.
        """
        return self.response.tool_chain.calls if self.response.tool_chain else []


class TraceabilityScenario:
    """Runs Moment 5: a single question that chains four read-only MCP calls."""

    def __init__(
        self,
        orchestrator: RAGOrchestrator,
        gateway: GatewayInterface,
    ) -> None:
        """Initialize the scenario.

        Args:
            orchestrator: Used to answer the sprint-status question and
                trigger the MCP tool chain.
            gateway: Used to reset cache state before running. The
                sprint-status question text never changes, but the MCP
                tool results behind it can (tasks move, sprints
                progress) — without resetting cache, a repeated run
                could show a stale answer generated from old tool data,
                even though the tool calls themselves always execute
                fresh.
        """
        self._orchestrator = orchestrator
        self._gateway = gateway

    async def run(
        self,
        question: str = SPRINT_STATUS_QUESTION,
    ) -> TraceabilityScenarioResult:
        """Answer the sprint-status question and report the tool chain outcome.

        Args:
            question: The question to ask. Defaults to the fixed
                sprint-status question used live in the demo.

        Returns:
            The response, plus tool-call count and success status.
        """
        await self._gateway.set_cache_enabled(False)
        response = await self._orchestrator.handle_question(question)
        return TraceabilityScenarioResult(response=response)
