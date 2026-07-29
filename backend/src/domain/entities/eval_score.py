"""Entities related to quality evaluation (RAGAS / DeepEval)."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvalScore:
    """Scores for a single query/response/context triple.

    Faithfulness and relevancy are the two scores the webinar demo
    specifically contrasts (Moment 2 and Moment 3), so they are
    first-class fields rather than buried in a generic dict.

    Attributes:
        relevancy: How on-topic the answer is with respect to the
            question, from 0.0 to 1.0.
        faithfulness: How grounded the answer is in the retrieved
            context, from 0.0 to 1.0.
        evaluator_name: Which evaluator produced this score — "ragas" or
            "deepeval".
        extra_metrics: Any additional metrics the evaluator reports
            beyond relevancy/faithfulness (e.g. context precision).
    """

    relevancy: float
    faithfulness: float
    evaluator_name: str
    extra_metrics: dict = field(default_factory=dict)

    @property
    def is_quality_trap(
        self,
    ) -> bool:
        """Return True if this score exhibits the Moment 2 failure mode.

        The "quality trap" is high relevancy paired with low
        faithfulness — an answer that looks on-topic but isn't actually
        grounded in the retrieved context.
        """
        return self.relevancy >= 0.7 and self.faithfulness < 0.5
