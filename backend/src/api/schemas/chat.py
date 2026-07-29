"""Request/response schemas for the /chat endpoint."""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Payload for POST /chat/.

    Attributes:
        question: The user's natural-language question.
        use_contextual_retrieval: Whether to use contextual retrieval
            instead of plain retrieval. See Moment 3 of the demo.
    """

    question: str
    use_contextual_retrieval: bool = False


class ChatResponse(BaseModel):
    """Response body for POST /chat/.

    Attributes:
        answer: The generated answer text.
        model_used: The model that actually produced the answer.
        cost_usd: The cost of this request, as reported by the gateway.
        latency_ms: How long generation took, in milliseconds.
        cache_hit: Whether the answer was served from the gateway cache.
        tool_calls: The names of any MCP tools called while answering.
        trace_url: A link to this request's trace in the observability
            backend, if available.
    """

    answer: str
    model_used: str
    cost_usd: float
    latency_ms: float
    cache_hit: bool
    tool_calls: list[str] = []
    trace_url: str | None = None
