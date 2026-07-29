"""Moment 1 — Cost Optimization.

Thin wrapper: toggles the gateway's cache/routing state, then runs the
same question through the orchestrator so a before/after cost comparison
can be read off the GenerationResult.

Does not reimplement retrieval/generation — delegates to RAGOrchestrator.
"""
from dataclasses import dataclass

from src.core.rag_orchestrator import RAGOrchestrator, RAGResponse
from src.domain.interfaces.gateway import GatewayInterface


@dataclass
class CostScenarioResult:
    """The before/after results of running the cost scenario.

    Attributes:
        before: The response with caching and routing disabled.
        after: The response with caching and routing enabled.
    """

    before: RAGResponse
    after: RAGResponse

    @property
    def cost_delta_usd(
        self,
    ) -> float:
        """Return how much cost was saved by enabling caching/routing."""
        return self.before.generation.cost_usd - self.after.generation.cost_usd


class CostScenario:
    """Runs Moment 1: cache/routing off, then on, for the same question."""

    def __init__(
        self,
        orchestrator: RAGOrchestrator,
        gateway: GatewayInterface,
    ) -> None:
        """Initialize the scenario.

        Args:
            orchestrator: Used to actually answer the question.
            gateway: Used to toggle caching and routing live.
        """
        self._orchestrator = orchestrator
        self._gateway = gateway

    async def run(
        self,
        question: str,
    ) -> CostScenarioResult:
        """Run the question with caching/routing off, then on.

        Args:
            question: The question to ask in both states.

        Returns:
            Both responses, plus a computed cost delta.
        """
        await self._gateway.set_cache_enabled(False)
        await self._gateway.set_routing_enabled(False)
        before = await self._orchestrator.handle_question(question)

        await self._gateway.set_cache_enabled(True)
        await self._gateway.set_routing_enabled(True)
        after = await self._orchestrator.handle_question(question)

        return CostScenarioResult(
            before=before,
            after=after,
        )
