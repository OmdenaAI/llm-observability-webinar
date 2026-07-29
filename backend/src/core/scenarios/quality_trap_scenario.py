"""Moment 2 — Quality Trap: High Relevancy, Low Faithfulness.

Runs a fixed trap-case question through the orchestrator, then scores the
result with the online evaluator (RAGAS). The trap case itself is fixed
demo data — see data/corpus and scenarios/trap_case notes in docs.
"""
from dataclasses import dataclass

from src.core.rag_orchestrator import RAGOrchestrator, RAGResponse
from src.domain.entities.eval_score import EvalScore
from src.domain.interfaces.evaluator import EvaluatorInterface
from src.domain.interfaces.gateway import GatewayInterface


@dataclass
class QualityTrapResult:
    """The result of running the quality trap scenario.

    Attributes:
        response: The full RAG response for the trap question.
        eval_score: The relevancy/faithfulness scores for that response.
    """

    response: RAGResponse
    eval_score: EvalScore


class QualityTrapScenario:
    """Runs Moment 2: forces a high-relevancy/low-faithfulness answer."""

    def __init__(
        self,
        orchestrator: RAGOrchestrator,
        evaluator: EvaluatorInterface,
        gateway: GatewayInterface,
    ) -> None:
        """Initialize the scenario.

        Args:
            orchestrator: Used to answer the trap question.
            evaluator: Used to score the resulting answer.
            gateway: Used to reset cache state before running, so this
                moment always gets a fresh generation rather than
                potentially replaying a cached response left over from
                testing another moment first.
        """
        self._orchestrator = orchestrator
        self._evaluator = evaluator
        self._gateway = gateway

    async def run(
        self,
        trap_question: str,
    ) -> QualityTrapResult:
        """Run the trap question and score the answer.

        Args:
            trap_question: The fixed question known to trigger the
                quality trap failure mode.

        Returns:
            The response and its evaluation score.
        """
        # Reset to a clean baseline — this scenario's whole point is
        # scoring a genuine generation, not a cached one from an earlier
        # test run.
        await self._gateway.set_cache_enabled(False)

        response = await self._orchestrator.handle_question(trap_question)

        eval_score = await self._evaluator.score(
            question=trap_question,
            answer=response.answer,
            context=response.retrieval.chunks if response.retrieval else [],
        )

        return QualityTrapResult(
            response=response,
            eval_score=eval_score,
        )
