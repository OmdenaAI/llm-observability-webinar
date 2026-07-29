"""Contract for a quality evaluator (RAGAS online, DeepEval CI).

Only the online evaluator is called from the live request path
(Moments 2 and 3). DeepEval implements this same interface for symmetry
and testability, but is invoked from the CI test suite, not the API.
"""
from abc import ABC, abstractmethod

from src.domain.entities.eval_score import EvalScore
from src.domain.entities.query import RetrievedChunk


class EvaluatorInterface(ABC):
    """Abstract contract for scoring a question/answer/context triple."""

    @abstractmethod
    async def score(
        self,
        question: str,
        answer: str,
        context: list[RetrievedChunk],
    ) -> EvalScore:
        """Score an answer for relevancy and faithfulness.

        Args:
            question: The original question asked.
            answer: The generated answer to evaluate.
            context: The chunks the answer should be grounded in.

        Returns:
            The relevancy/faithfulness scores for this triple.
        """
        raise NotImplementedError
