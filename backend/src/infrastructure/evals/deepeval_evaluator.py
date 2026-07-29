"""DeepEval-based evaluator — implements the same EvaluatorInterface as
RAGAS for symmetry and testability, but is invoked only from
tests/e2e or a dedicated CI pytest suite (see docs/architecture_plan.md —
"DeepEval gap" note). Not wired into any live demo moment.

Judge model is configurable — OpenAI (default) or Anthropic — same
pattern as RagasEvaluator, set via EVAL_JUDGE_PROVIDER / EVAL_JUDGE_MODEL.
"""
from src.domain.entities.eval_score import EvalScore
from src.domain.entities.query import RetrievedChunk
from src.infrastructure.evals.base import BaseEvaluator


class DeepEvalEvaluator(BaseEvaluator):
    """Evaluator that scores answers using DeepEval's CI-oriented metrics."""

    def __init__(
        self,
        judge_provider: str = "openai",
        judge_model: str = "gpt-4o-mini",
        openai_api_key: str = "",
        anthropic_api_key: str = "",
    ) -> None:
        """Initialize the evaluator's judge model configuration.

        Args:
            judge_provider: Which provider's chat model to use as the
                judge — "openai" or "anthropic".
            judge_model: The specific model name to use as the judge
                (e.g. "gpt-4o-mini" or "claude-3-5-sonnet-latest").
            openai_api_key: API key used if judge_provider is "openai".
            anthropic_api_key: API key used if judge_provider is
                "anthropic".
        """
        self._judge_provider = judge_provider
        self._judge_model = judge_model
        self._openai_api_key = openai_api_key
        self._anthropic_api_key = anthropic_api_key
        # TODO: DeepEval's metrics accept a `model` param on each metric
        # instance (e.g. FaithfulnessMetric(model=...)). Construct the
        # appropriate DeepEval model wrapper here based on judge_provider —
        # DeepEval has native OpenAI support; Anthropic typically requires
        # wrapping via DeepEval's custom LLM interface.

    async def _do_score(
        self,
        question: str,
        answer: str,
        context: list[RetrievedChunk],
    ) -> EvalScore:
        """Score an answer using DeepEval's faithfulness and relevancy metrics.

        Args:
            question: The original question asked.
            answer: The generated answer to evaluate.
            context: The chunks the answer should be grounded in.
        """
        # TODO: run the relevant DeepEval metrics (e.g. FaithfulnessMetric,
        # AnswerRelevancyMetric) as a CI-time check, map to EvalScore.
        raise NotImplementedError(
            "DeepEvalEvaluator._do_score: pending implementation"
        )
