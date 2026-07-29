"""Contract for the tracing/instrumentation layer.

core/ and infrastructure/services/ call this interface to record spans —
they never import OpenTelemetry or OpenLLMetry directly. Swapping the
observability backend (Langfuse <-> Phoenix) only touches
infrastructure/tracing/*.
"""
from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager

from src.domain.entities.trace_span import SpanKind


class TracerInterface(ABC):
    """Abstract contract for recording spans and resolving trace URLs."""

    @abstractmethod
    def start_span(
        self,
        name: str,
        kind: SpanKind,
        attributes: dict | None = None,
    ) -> AbstractAsyncContextManager:
        """Return an async context manager that records a span on exit.

        Usage:
            async with tracer.start_span(
                "retrieve",
                SpanKind.RETRIEVAL,
            ) as span:
                result = await do_retrieval()
                span.set_attribute(
                    "chunks_returned",
                    len(result.chunks),
                )

        Args:
            name: A human-readable name for the span.
            kind: The category of operation this span represents.
            attributes: Optional initial attributes to attach to the span.

        Returns:
            An async context manager that starts the span on entry and
            ends it (recording duration and status) on exit.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_trace_url(
        self,
        trace_id: str,
    ) -> str | None:
        """Return a link to view this trace in the observability backend.

        Args:
            trace_id: The identifier of the trace to link to.

        Returns:
            A URL into Langfuse or Phoenix, or None if no such link is
            available.
        """
        raise NotImplementedError

    @abstractmethod
    def get_current_trace_id(
        self,
    ) -> str | None:
        """Return the trace ID of the currently active span, if any.

        Synchronous, matching the underlying OTel API (reading the
        current span context is not an I/O operation). Intended to be
        called from within an active `start_span` block — e.g. the root
        span wrapping a whole request — so the caller can build a
        trace_url afterward via `get_trace_url`.

        Returns:
            The current trace ID as a hex string, or None if there is
            no active span.
        """
        raise NotImplementedError
