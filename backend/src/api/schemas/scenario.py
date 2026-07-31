"""Request/response schemas for the /scenarios and /admin endpoints —
one pair of models per demo moment, mirroring core/scenarios/*.py."""
from pydantic import BaseModel


class CostScenarioResponse(BaseModel):
    """Response body for POST /scenarios/cost (Moment 1)."""

    before_cost_usd: float
    after_cost_usd: float
    cost_delta_usd: float
    before_cache_hit: bool
    after_cache_hit: bool


class QualityTrapResponse(BaseModel):
    """Response body for POST /scenarios/quality-trap (Moment 2)."""

    answer: str
    relevancy: float
    faithfulness: float
    is_quality_trap: bool
    retrieved_sources: list[str] = []


class ContextComparisonResponse(BaseModel):
    """Response body for POST /scenarios/context-comparison (Moment 3, part 1)."""

    plain_faithfulness: float
    contextual_faithfulness: float
    faithfulness_delta: float
    plain_sources: list[str] = []
    contextual_sources: list[str] = []


class ContextSingleTurnResponse(BaseModel):
    """Response body for POST /scenarios/context-single (Moment 3, interactive flow).

    Represents ONE answer under ONE retrieval mode — used by the UI's
    ask-toggle-ask flow, where the presenter asks once with contextual
    retrieval off, then again with it on, watching the score change
    across two real, separate turns rather than one combined comparison.
    """

    answer: str
    relevancy: float
    faithfulness: float
    retrieval_mode: str
    trace_url: str | None = None
    retrieved_sources: list[str] = []


class StaleContextResponse(BaseModel):
    """Response body for POST /scenarios/stale-context (Moment 3, part 2)."""

    answer: str
    faithfulness: float
    passes_eval_but_wrong: bool
    retrieved_sources: list[str] = []


class ReliabilityScenarioRequest(BaseModel):
    """Payload for POST /scenarios/reliability (Moment 4)."""

    question: str


class ReliabilityScenarioResponse(BaseModel):
    """Response body for POST /scenarios/reliability (Moment 4)."""

    answer: str
    failed_over: bool


class ToolCallDetail(BaseModel):
    """One individual MCP tool call's outcome, within a traceability result."""

    tool_name: str
    status: str
    latency_ms: float
    error_message: str | None = None


class TraceabilityScenarioResponse(BaseModel):
    """Response body for POST /scenarios/traceability (Moment 5)."""

    answer: str
    tool_call_count: int
    all_calls_succeeded: bool
    tool_calls: list[ToolCallDetail]
    trace_url: str | None = None


class GatewayToggleRequest(BaseModel):
    """Payload for POST /admin/gateway/cache and /admin/gateway/routing."""

    enabled: bool