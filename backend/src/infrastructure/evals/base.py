"""Abstract base for evaluator implementations."""
from abc import abstractmethod

from src.domain.entities.eval_score import EvalScore
from src.domain.entities.query import RetrievedChunk
from src.domain.interfaces.evaluator import EvaluatorInterface
from utils.logger import get_logger

logger = get_logger()


class BaseEvaluator(EvaluatorInterface):
    """Shared logging around concrete evaluator scoring calls."""

    async def score(
        self,
        question: str,
        answer: str,
        context: list[RetrievedChunk],
    ) -> EvalScore:
        """Log and delegate to the concrete evaluator's scoring logic.

        Args:
            question: The original question asked.
            answer: The generated answer to evaluate.
            context: The chunks the answer should be grounded in.

        Returns:
            The relevancy/faithfulness scores for this triple.
        """
        logger.debug(f"Scoring answer for question: {question!r}")
        return await self._do_score(question, answer, context)

    @abstractmethod
    async def _do_score(
        self,
        question: str,
        answer: str,
        context: list[RetrievedChunk],
    ) -> EvalScore:
        """Perform the actual scoring against the concrete evaluator library.

        Args:
            question: The original question asked.
            answer: The generated answer to evaluate.
            context: The chunks the answer should be grounded in.
        """
        raise NotImplementedError
