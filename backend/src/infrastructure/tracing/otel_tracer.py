"""OTel-based tracer, using OpenTelemetry's GenAI semantic conventions
directly (gen_ai.operation.name and friends).

Exports DIRECTLY to Langfuse and/or Phoenix's own OTLP endpoints — not
via an intermediate OTel Collector. An earlier version of this routed
through infra/otel-collector-config.yaml + a dedicated collector
container, but that container repeatedly failed to start reliably
across several live runs (DNS resolution errors from the backend's
side, persisting across multiple config fixes — collector-specific
env-var syntax, missing env_file, the basicauth extension). Direct
SDK-to-backend export removes an entire moving part and its startup
ordering complexity; the collector's main advantage (routing one
stream to many backends via config alone, no code change) isn't worth
its reliability cost for a two-destination demo. The collector config
is left in infra/ as a documented alternative, not deleted.
"""
import base64
from contextlib import asynccontextmanager

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExportResult
from opentelemetry.trace import Status, StatusCode

from src.domain.entities.trace_span import SpanKind
from src.infrastructure.tracing.base import BaseTracer
from utils.logger import get_logger

logger = get_logger()

# Maps our domain-level SpanKind to OTel's GenAI semantic convention
# operation names (gen_ai.operation.name). REQUEST uses "invoke_agent"
# since it wraps the whole retrieve->generate->tool-call flow, not a
# single model call.
_SPAN_KIND_TO_GENAI_OPERATION = {
    SpanKind.REQUEST: "invoke_agent",
    SpanKind.RETRIEVAL: "retrieval",
    SpanKind.GENERATION: "chat",
    SpanKind.TOOL_CALL: "execute_tool",
    SpanKind.EVAL: "evaluate",
}

_SERVICE_NAME = "llm-observability-demo"


class _LoggingOTLPSpanExporter(OTLPSpanExporter):
    """OTLPSpanExporter subclass that logs every export attempt explicitly.

    The base SDK exporter is silent on success — only failures produce
    a log line (via BatchSpanProcessor's own internal logger). That
    makes "export succeeded" and "export was never actually attempted
    yet" indistinguishable from the logs alone, which was a real
    diagnostic dead end while debugging Langfuse connectivity (Phoenix's
    failures were visible via DNS errors; Langfuse produced no output
    either way, silence being consistent with both success and several
    failure modes). This makes every attempt visible regardless of
    outcome.
    """

    def __init__(
        self,
        *args,
        backend_label: str = "unknown",
        **kwargs,
    ) -> None:
        """Initialize the exporter, storing a human-readable label for logging.

        Args:
            *args: Forwarded to OTLPSpanExporter.
            backend_label: A short name (e.g. "langfuse", "phoenix")
                used to identify this exporter's log lines.
            **kwargs: Forwarded to OTLPSpanExporter.
        """
        super().__init__(*args, **kwargs)
        self._backend_label = backend_label

    def export(
        self,
        spans,
    ) -> SpanExportResult:
        """Export spans, logging the outcome explicitly either way.

        Args:
            spans: The spans to export.
        """
        result = super().export(spans)
        if result == SpanExportResult.SUCCESS:
            logger.info(
                f"[{self._backend_label}] Exported {len(spans)} span(s) successfully"
            )
        else:
            logger.error(
                f"[{self._backend_label}] Failed to export {len(spans)} span(s) "
                f"— result={result}"
            )
        return result


class OTelTracer(BaseTracer):
    """Tracer that exports OTel spans directly to Langfuse and/or Phoenix."""

    def __init__(
        self,
        collector_endpoint: str,
        observability_backend: str,
        langfuse_host: str = "",
        phoenix_host: str = "",
        langfuse_public_key: str = "",
        langfuse_secret_key: str = "",
        phoenix_internal_host: str = "",
    ) -> None:
        """Initialize the tracer's exporters and provider.

        Args:
            collector_endpoint: Unused by direct export — kept as a
                constructor param so the DI container binding doesn't
                need to change if a collector-based path is reinstated
                later. See module docstring.
            observability_backend: Retained for compatibility with
                get_trace_url's link construction; direct export
                sends to BOTH configured backends regardless of this
                value (they're independent span processors), but the
                trace URL shown to the presenter still needs to know
                which one to link to.
            langfuse_host: Langfuse's base URL (e.g.
                "https://cloud.langfuse.com"). Used both for export and
                for the browser-facing trace_url — Langfuse Cloud is a
                real internet host, reachable identically from inside
                the container and from the presenter's browser, so no
                internal/external split is needed here (unlike Phoenix).
                If empty, or if the public/secret key are empty,
                Langfuse export is skipped.
            phoenix_host: Phoenix's HOST-MAPPED base URL (e.g.
                "http://localhost:6006") — used ONLY for the
                browser-facing trace_url link. NOT used for export; see
                phoenix_internal_host.
            langfuse_public_key: Used to build the Basic Auth header
                Langfuse's OTLP endpoint requires (base64 of
                "public_key:secret_key" — confirmed against Langfuse's
                current docs).
            langfuse_secret_key: See langfuse_public_key.
            phoenix_internal_host: Phoenix's DOCKER-INTERNAL base URL
                (e.g. "http://phoenix:6006", the compose service name)
                — used for the actual export call, since that request
                originates from inside the backend container, not the
                presenter's browser. Using phoenix_host here instead
                was a real bug: "localhost" inside the container means
                the container itself, not the Phoenix container, so
                exports would silently go nowhere.
        """
        self._observability_backend = observability_backend
        self._langfuse_host = langfuse_host
        self._phoenix_host = phoenix_host

        resource = Resource.create({"service.name": _SERVICE_NAME})
        provider = TracerProvider(resource=resource)

        exporters_configured = []

        if langfuse_host and langfuse_public_key and langfuse_secret_key:
            auth_string = f"{langfuse_public_key}:{langfuse_secret_key}"
            auth_b64 = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
            langfuse_exporter = _LoggingOTLPSpanExporter(
                endpoint=f"{langfuse_host.rstrip('/')}/api/public/otel/v1/traces",
                headers={"Authorization": f"Basic {auth_b64}"},
                backend_label="langfuse",
            )
            provider.add_span_processor(BatchSpanProcessor(langfuse_exporter))
            exporters_configured.append("langfuse")
        else:
            logger.warning(
                "Langfuse export skipped — langfuse_host, "
                "langfuse_public_key, or langfuse_secret_key is empty."
            )

        if phoenix_internal_host:
            phoenix_exporter = _LoggingOTLPSpanExporter(
                endpoint=f"{phoenix_internal_host.rstrip('/')}/v1/traces",
                backend_label="phoenix",
            )
            provider.add_span_processor(BatchSpanProcessor(phoenix_exporter))
            exporters_configured.append("phoenix")
        else:
            logger.warning(
                "Phoenix export skipped — phoenix_internal_host is empty."
            )

        if not exporters_configured:
            logger.warning(
                "No observability backend configured — spans will be "
                "created but never exported anywhere."
            )
        else:
            logger.info(f"OTel direct export configured for: {exporters_configured}")

        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(_SERVICE_NAME)

    @asynccontextmanager
    async def start_span(
        self,
        name: str,
        kind: SpanKind,
        attributes: dict | None = None,
    ):
        """Start a real OTel span for the duration of the `async with` block.

        Sets `gen_ai.operation.name` from the SpanKind mapping, plus any
        caller-supplied attributes (only primitive-typed values are
        passed through — OTel attributes must be str/int/float/bool or
        homogeneous sequences of those). On exception, marks the span's
        status as an error before re-raising, so failures are visible in
        the trace waterfall rather than just looking like a span that
        happened to end.

        Args:
            name: A human-readable name for the span.
            kind: The category of operation this span represents.
            attributes: Optional initial attributes to attach to the span.
        """
        otel_attributes = {
            "gen_ai.operation.name": _SPAN_KIND_TO_GENAI_OPERATION.get(
                kind,
                kind.value,
            ),
        }
        if attributes:
            for key, value in attributes.items():
                if isinstance(value, (str, int, float, bool)):
                    otel_attributes[key] = value
                else:
                    # Non-primitive attribute values (e.g. nested dicts)
                    # aren't valid OTel attribute types — stringify rather
                    # than silently dropping them, so at least the value
                    # is visible in the trace even if not queryable.
                    otel_attributes[key] = str(value)

        with self._tracer.start_as_current_span(
            name,
            attributes=otel_attributes,
        ) as span:
            try:
                yield span
            except Exception as exc:
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise

    def get_current_trace_id(
        self,
    ) -> str | None:
        """Return the trace ID of the currently active span, as hex.

        Returns:
            The 32-hex-character trace ID, or None if there is no
            active span (e.g. called outside any start_span block).
        """
        current_span = trace.get_current_span()
        span_context = current_span.get_span_context()
        if not span_context.is_valid:
            return None
        return format(span_context.trace_id, "032x")

    async def get_trace_url(
        self,
        trace_id: str,
    ) -> str | None:
        """Construct a deep link into the configured observability backend.

        Args:
            trace_id: The identifier of the trace to link to.

        Returns:
            A best-effort URL into Langfuse or Phoenix, preferring
            whichever `observability_backend` names, falling back to
            whichever is actually configured. URL path formats are not
            exhaustively confirmed against current provider docs — verify
            against a real trace and adjust here if the link 404s.
        """
        if self._observability_backend == "langfuse" and self._langfuse_host:
            return f"{self._langfuse_host.rstrip('/')}/trace/{trace_id}"
        if self._observability_backend == "phoenix" and self._phoenix_host:
            return f"{self._phoenix_host.rstrip('/')}/tracing/traces/{trace_id}"
        if self._langfuse_host:
            return f"{self._langfuse_host.rstrip('/')}/trace/{trace_id}"
        if self._phoenix_host:
            return f"{self._phoenix_host.rstrip('/')}/tracing/traces/{trace_id}"
        return None
