"""Wraps an EvaluatorInterface.

Reserved as the extension point for future cross-cutting eval concerns
(e.g. caching scores for identical question/answer/context triples so
repeated dry runs don't re-score unnecessarily).
"""
from src.domain.entities.eval_score import EvalScore
from src.domain.entities.query import RetrievedChunk
from src.domain.interfaces.evaluator import EvaluatorInterface


class EvalService(EvaluatorInterface):
    """Thin decorator around a concrete EvaluatorInterface."""

    def __init__(
        self,
        evaluator: EvaluatorInterface,
    ) -> None:
        """Initialize the service.

        Args:
            evaluator: The underlying evaluator to delegate to.
        """
        self._evaluator = evaluator

    async def score(
        self,
        question: str,
        answer: str,
        context: list[RetrievedChunk],
    ) -> EvalScore:
        """Delegate scoring to the underlying evaluator.

        Args:
            question: The original question asked.
            answer: The generated answer to evaluate.
            context: The chunks the answer should be grounded in.
        """
        return await self._evaluator.score(question, answer, context)
