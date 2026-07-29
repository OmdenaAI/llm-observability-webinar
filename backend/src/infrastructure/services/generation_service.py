"""Wraps an LLMProviderInterface with cross-cutting concerns.

Same rationale as RetrievalService — tracing lives in RAGOrchestrator;
this is the extension point for retry/backoff behavior around
generation specifically (e.g. retrying once on a gateway timeout before
surfacing an error), independent of the gateway's own failover logic.
"""
from src.domain.entities.generation import GenerationResult
from src.domain.entities.query import RetrievedChunk
from src.domain.interfaces.llm_provider import LLMProviderInterface


class GenerationService(LLMProviderInterface):
    """Retry-wrapping decorator around a concrete LLMProviderInterface."""

    def __init__(
        self,
        llm_provider: LLMProviderInterface,
        max_retries: int = 1,
    ) -> None:
        """Initialize the service.

        Args:
            llm_provider: The underlying LLM provider to delegate to.
            max_retries: How many additional attempts to make on
                generation failure before giving up.
        """
        self._llm_provider = llm_provider
        self._max_retries = max_retries

    async def generate(
        self,
        question: str,
        context: list[RetrievedChunk],
        model: str | None = None,
    ) -> GenerationResult:
        """Generate an answer, retrying on failure up to max_retries times.

        Args:
            question: The user's natural-language question.
            context: The retrieved chunks to ground the answer in.
            model: An optional specific model to use.

        Raises:
            Exception: The last error encountered, if all attempts fail.
        """
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._llm_provider.generate(question, context, model)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        raise last_error  # type: ignore[misc]

    async def health_check(
        self,
    ) -> bool:
        """Delegate the health check to the underlying provider."""
        return await self._llm_provider.health_check()
