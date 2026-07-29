"""Moment 4 — Reliability: Live Provider Outage.

Does not orchestrate a question itself in the "kill" step — the actual
provider kill is triggered externally (`make kill-provider` /
kill_provider.sh), mirroring how a real outage isn't triggered through
the app. This scenario's job is: run a question after the kill and
confirm the user-facing answer still comes back normally, while exposing
the failover metadata for the presenter to point at on the dashboard.
"""
from dataclasses import dataclass

from src.core.rag_orchestrator import RAGOrchestrator, RAGResponse
from src.domain.interfaces.gateway import GatewayInterface

# The exact LiteLLM model_name that make kill-provider stops (see
# infra/litellm-config.yaml and scripts/kill_provider.sh). Must be
# requested explicitly, not left to the provider's own routing policy —
# routing state is shared, global gateway state used by Moment 1, and if
# it's left over from testing another moment first, the natural request
# could resolve to a model that was never killed at all, making this
# scenario "succeed" without ever actually testing a failure.
KILLED_PROVIDER_MODEL = "primary-model"


@dataclass
class ReliabilityScenarioResult:
    """The result of running a question after a simulated provider outage.

    Attributes:
        response: The RAG response for the question, answered after the
            outage was triggered.
    """

    response: RAGResponse

    @property
    def failed_over(
        self,
    ) -> bool:
        """Return True if the generation result used a fallback path.

        Relies on infrastructure/gateway populating
        `failover_triggered` in GenerationResult.metadata — see
        litellm_gateway_provider.
        """
        return bool(self.response.generation.metadata.get("failover_triggered"))


class ReliabilityScenario:
    """Runs Moment 4: answers a question after the provider has been killed."""

    def __init__(
        self,
        orchestrator: RAGOrchestrator,
        gateway: GatewayInterface,
    ) -> None:
        """Initialize the scenario.

        Args:
            orchestrator: Used to answer the question after the outage.
            gateway: Used to reset cache state and restore the provider
                between dry runs.
        """
        self._orchestrator = orchestrator
        self._gateway = gateway

    async def run_after_outage(
        self,
        question: str,
    ) -> ReliabilityScenarioResult:
        """Answer a question, assuming the provider has already been killed.

        Call this only after the provider has been killed externally
        (e.g. via `make kill-provider`).

        Args:
            question: The question to ask post-outage. Use a question
                not asked before in this session — a cached response
                would return instantly without ever attempting a real
                network call, making the outage invisible either way.

        Returns:
            The response, plus whether a failover path was used.
        """
        # Disable caching so this call always makes a real network
        # attempt against the killed provider, regardless of whatever
        # cache state Moment 1 left behind.
        await self._gateway.set_cache_enabled(False)

        response = await self._orchestrator.handle_question(
            question,
            model=KILLED_PROVIDER_MODEL,
        )
        return ReliabilityScenarioResult(response=response)

    async def restore(
        self,
        provider_name: str,
    ) -> None:
        """Restore the given provider to a healthy state.

        Convenience wrapper so the API/CLI can reset state between dry
        runs without reaching into the gateway directly.

        Args:
            provider_name: The name of the provider to restore.
        """
        await self._gateway.restore_provider(provider_name)
