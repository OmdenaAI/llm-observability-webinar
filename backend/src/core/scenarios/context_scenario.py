"""Moment 3 — Context as a Lever.

Three ways to exercise this scenario:
1. run_single_turn — answer + score ONE question under a given
   retrieval mode. Used by the interactive UI flow: presenter toggles
   contextual retrieval off, asks, sees the score; toggles it on, asks
   the same question again, sees the score improve — as two real,
   separately visible turns rather than one button computing a diff.
2. run_comparison — both retrieval modes in one call, returning the
   delta directly. Kept for API/testing convenience; the UI no longer
   calls this directly (see (1) above) but it remains available.
3. run_stale_context_case — the stale-context failure case (eval
   passes, answer is still wrong), a separate fixed-question demo.
"""
from dataclasses import dataclass

from src.core.rag_orchestrator import RAGOrchestrator, RAGResponse
from src.domain.entities.eval_score import EvalScore
from src.domain.interfaces.evaluator import EvaluatorInterface
from src.domain.interfaces.gateway import GatewayInterface


@dataclass
class SingleContextTurnResult:
    """The result of answering and scoring one question under one
    retrieval mode.

    Attributes:
        response: The RAG response for this turn.
        eval_score: The evaluation score for that response.
    """

    response: RAGResponse
    eval_score: EvalScore


@dataclass
class ContextComparisonResult:
    """The result of comparing plain vs. contextual retrieval.

    Attributes:
        plain: The response using plain retrieval.
        plain_score: The evaluation score for that response.
        contextual: The response using contextual retrieval.
        contextual_score: The evaluation score for that response.
    """

    plain: RAGResponse
    plain_score: EvalScore
    contextual: RAGResponse
    contextual_score: EvalScore

    @property
    def faithfulness_delta(
        self,
    ) -> float:
        """Return how much faithfulness improved with contextual retrieval."""
        return self.contextual_score.faithfulness - self.plain_score.faithfulness


@dataclass
class StaleContextResult:
    """The result of running the stale-context case.

    Attributes:
        response: The RAG response for the stale-context question.
        eval_score: The evaluation score for that response.
    """

    response: RAGResponse
    eval_score: EvalScore

    @property
    def passes_eval_but_wrong(
        self,
    ) -> bool:
        """Return True when faithfulness looks fine but the answer is stale.

        The demo asserts this manually by knowing the expected correct
        answer for the fixed stale-context question; this flag only
        reflects the eval-score side of that mismatch.
        """
        return self.eval_score.faithfulness >= 0.7


class ContextScenario:
    """Runs Moment 3: contextual-retrieval comparison and the stale-context case."""

    def __init__(
        self,
        orchestrator: RAGOrchestrator,
        evaluator: EvaluatorInterface,
        gateway: GatewayInterface,
    ) -> None:
        """Initialize the scenario.

        Args:
            orchestrator: Used to answer both the comparison and
                stale-context questions.
            evaluator: Used to score each resulting answer.
            gateway: Used to reset cache state before each run — a
                cached response from a prior test would bypass the
                actual plain-vs-contextual comparison this moment exists
                to demonstrate.
        """
        self._orchestrator = orchestrator
        self._evaluator = evaluator
        self._gateway = gateway

    async def run_single_turn(
        self,
        question: str,
        use_contextual_retrieval: bool,
    ) -> SingleContextTurnResult:
        """Answer and score one question under one retrieval mode.

        Args:
            question: The question to ask.
            use_contextual_retrieval: Which retrieval mode to use for
                this turn.

        Returns:
            The response and its evaluation score.
        """
        await self._gateway.set_cache_enabled(False)

        response = await self._orchestrator.handle_question(
            question,
            use_contextual_retrieval=use_contextual_retrieval,
        )
        eval_score = await self._evaluator.score(
            question=question,
            answer=response.answer,
            context=response.retrieval.chunks if response.retrieval else [],
        )
        return SingleContextTurnResult(
            response=response,
            eval_score=eval_score,
        )

    async def run_comparison(
        self,
        question: str,
    ) -> ContextComparisonResult:
        """Run the same question with plain, then contextual, retrieval.

        Args:
            question: The question to ask under both retrieval modes.

        Returns:
            Both responses, their scores, and the faithfulness delta.
        """
        await self._gateway.set_cache_enabled(False)

        plain = await self._orchestrator.handle_question(
            question,
            use_contextual_retrieval=False,
        )
        plain_score = await self._evaluator.score(
            question=question,
            answer=plain.answer,
            context=plain.retrieval.chunks if plain.retrieval else [],
        )

        contextual = await self._orchestrator.handle_question(
            question,
            use_contextual_retrieval=True,
        )
        contextual_score = await self._evaluator.score(
            question=question,
            answer=contextual.answer,
            context=contextual.retrieval.chunks if contextual.retrieval else [],
        )

        return ContextComparisonResult(
            plain=plain,
            plain_score=plain_score,
            contextual=contextual,
            contextual_score=contextual_score,
        )

    async def run_stale_context_case(
        self,
        stale_question: str,
    ) -> StaleContextResult:
        """Run the fixed stale-context question and score the answer.

        Args:
            stale_question: The fixed question known to retrieve the
                deliberately outdated document.

        Returns:
            The response and its evaluation score.
        """
        await self._gateway.set_cache_enabled(False)

        response = await self._orchestrator.handle_question(
            stale_question,
            use_contextual_retrieval=True,
        )
        eval_score = await self._evaluator.score(
            question=stale_question,
            answer=response.answer,
            context=response.retrieval.chunks if response.retrieval else [],
        )
        return StaleContextResult(
            response=response,
            eval_score=eval_score,
        )
