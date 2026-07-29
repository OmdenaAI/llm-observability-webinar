"""Entities related to LLM generation."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GenerationResult:
    """The output of an LLM call, plus cost/latency metadata needed for the demo.

    Attributes:
        answer: The generated answer text.
        model_used: The name of the model that actually produced the
            answer — may differ from the model requested if the gateway's
            routing or failover logic substituted a different one.
        prompt_tokens: Number of tokens in the prompt sent to the model.
        completion_tokens: Number of tokens in the generated completion.
        cost_usd: The cost of this generation, as reported by the gateway.
        latency_ms: Wall-clock time the generation call took, in
            milliseconds.
        cache_hit: Whether this result was served from the gateway's
            cache rather than a fresh model call. Used by Moment 1.
        metadata: Additional gateway-specific data, including
            `failover_triggered` (bool), used by the reliability scenario
            (Moment 4) to detect whether a fallback path was taken.
    """

    answer: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: float
    cache_hit: bool = False
    metadata: dict = field(default_factory=dict)
