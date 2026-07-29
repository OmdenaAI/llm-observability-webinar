"""Abstract base for LLM provider implementations."""
import time
from abc import abstractmethod

from src.domain.entities.generation import GenerationResult
from src.domain.entities.query import RetrievedChunk
from src.domain.interfaces.llm_provider import LLMProviderInterface
from utils.logger import get_logger

logger = get_logger()


class BaseLLMProvider(LLMProviderInterface):
    """Shared prompt construction and latency timing.

    Concrete providers implement only the actual call to the
    model/gateway via `_call_model`.
    """

    def build_prompt(
        self,
        question: str,
        context: list[RetrievedChunk],
    ) -> str:
        """Construct the prompt sent to the model.

        Each chunk is labeled with its source. This matters now that
        `context` can contain a mix of retrieved document chunks and
        MCP tool call results (see RAGOrchestrator._generate) — without
        a label, the model has no way to tell "text from a policy doc"
        apart from "live JSON from a kanban board," which affects how
        it should be interpreted and cited in the answer.

        Args:
            question: The user's natural-language question.
            context: The retrieved chunks and/or tool results to ground
                the answer in.

        Returns:
            The fully assembled prompt string.
        """
        context_block = "\n\n".join(
            f"[Source: {chunk.source}]\n{chunk.content}" for chunk in context
        )
        return (
            "Answer the question using only the provided context.\n\n"
            f"Context:\n{context_block}\n\n"
            f"Question: {question}"
        )

    async def generate(
        self,
        question: str,
        context: list[RetrievedChunk],
        model: str | None = None,
    ) -> GenerationResult:
        """Build the prompt, time the model call, and return the result.

        Args:
            question: The user's natural-language question.
            context: The retrieved chunks to ground the answer in.
            model: An optional specific model to use.

        Returns:
            The generated answer, along with cost/latency metadata.
        """
        prompt = self.build_prompt(question, context)
        start = time.perf_counter()
        result = await self._call_model(prompt, model)
        latency_ms = (time.perf_counter() - start) * 1000
        logger.debug(f"Generation completed in {latency_ms:.1f}ms")
        return result

    @abstractmethod
    async def _call_model(
        self,
        prompt: str,
        model: str | None,
    ) -> GenerationResult:
        """Call the concrete model/gateway with the given prompt.

        Args:
            prompt: The fully assembled prompt string.
            model: An optional specific model to use.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(
        self,
    ) -> bool:
        """Return True if the underlying provider/gateway is reachable."""
        raise NotImplementedError
