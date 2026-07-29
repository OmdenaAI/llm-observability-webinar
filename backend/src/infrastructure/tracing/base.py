"""Abstract base for tracer implementations."""
from abc import abstractmethod

from src.domain.interfaces.tracer import TracerInterface


class BaseTracer(TracerInterface):
    """Reserved extension point for shared span-naming or
    attribute-normalization logic if multiple tracing backends need it.

    Currently a thin pass-through with no shared behavior of its own.
    """

    @abstractmethod
    def start_span(
        self,
        name,
        kind,
        attributes=None,
    ):
        """Start a new span. See TracerInterface.start_span for details."""
        raise NotImplementedError

    @abstractmethod
    async def get_trace_url(
        self,
        trace_id: str,
    ) -> str | None:
        """Return a link to view this trace in the observability backend.

        Args:
            trace_id: The identifier of the trace to link to.
        """
        raise NotImplementedError

    @abstractmethod
    def get_current_trace_id(
        self,
    ) -> str | None:
        """Return the trace ID of the currently active span, if any."""
        raise NotImplementedError
