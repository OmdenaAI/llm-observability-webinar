"""Contract every LLM provider/gateway implementation must satisfy."""
from abc import ABC, abstractmethod

from src.domain.entities.generation import GenerationResult
from src.domain.entities.query import RetrievedChunk


class LLMProviderInterface(ABC):
    """Abstract contract for generating an answer from a question and context."""

    @abstractmethod
    async def generate(
        self,
        question: str,
        context: list[RetrievedChunk],
        model: str | None = None,
    ) -> GenerationResult:
        """Generate an answer given a question and retrieved context.

        Args:
            question: The user's natural-language question.
            context: The retrieved chunks to ground the answer in.
            model: An optional specific model to use. Implementations
                that route through a gateway (e.g. LiteLLM) may ignore
                this in favor of their own routing rules.

        Returns:
            The generated answer, along with cost/latency/cache metadata.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(
        self,
    ) -> bool:
        """Return True if the underlying provider/gateway is reachable."""
        raise NotImplementedError
