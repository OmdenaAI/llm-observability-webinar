"""Entity representing a single observability span.

This is a domain-level shape — infrastructure/tracing implementations
translate to/from whatever the underlying exporter (OTel/OpenLLMetry)
needs, but core/services never depend on that library-specific shape
directly.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SpanKind(str, Enum):
    """The category of operation a trace span represents."""

    REQUEST = "request"
    RETRIEVAL = "retrieval"
    GENERATION = "generation"
    TOOL_CALL = "tool_call"
    EVAL = "eval"


@dataclass(frozen=True)
class TraceSpan:
    """A single step in a request's trace.

    Attributes:
        name: A human-readable name for this span (e.g. "retrieve",
            "mcp:sprints_get_active").
        kind: The category of operation this span represents.
        started_at: When the span began.
        duration_ms: How long the span lasted, in milliseconds.
        cost_usd: The cost attributable to this span, if applicable.
        status: The outcome of the span — "ok" or an error description.
        attributes: Any additional span-specific data.
    """

    name: str
    kind: SpanKind
    started_at: datetime
    duration_ms: float
    cost_usd: float | None = None
    status: str = "ok"
    attributes: dict = field(default_factory=dict)
