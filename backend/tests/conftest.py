"""Shared fixtures — primarily mocked domain interfaces, so unit tests
never touch real infrastructure."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.entities.eval_score import EvalScore
from src.domain.entities.generation import GenerationResult
from src.domain.entities.query import Query, RetrievalResult, RetrievedChunk
from src.domain.entities.tool_call import ToolCallResult, ToolCallStatus, ToolChain


@pytest.fixture
def sample_chunk() -> RetrievedChunk:
    """Return a single retrieved chunk for use in retrieval-related fixtures."""
    return RetrievedChunk(
        content="Sample context.",
        source="test.md",
        score=0.9,
    )


@pytest.fixture
def sample_retrieval_result(
    sample_chunk,
) -> RetrievalResult:
    """Return a retrieval result wrapping a single sample chunk."""
    return RetrievalResult(
        query=Query(text="What is X?"),
        chunks=[sample_chunk],
        retrieval_mode="plain",
    )


@pytest.fixture
def sample_generation_result() -> GenerationResult:
    """Return a generic successful generation result."""
    return GenerationResult(
        answer="X is Y.",
        model_used="test-model",
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=0.001,
        latency_ms=120.0,
        cache_hit=False,
    )


@pytest.fixture
def sample_eval_score() -> EvalScore:
    """Return a generic high-quality eval score (not a quality trap)."""
    return EvalScore(
        relevancy=0.9,
        faithfulness=0.85,
        evaluator_name="ragas",
    )


@pytest.fixture
def sample_tool_chain() -> ToolChain:
    """Return a tool chain containing a single successful tool call."""
    return ToolChain(
        calls=[
            ToolCallResult(
                tool_name="sprints_get_active",
                arguments={},
                result={"sprint_id": "123"},
                status=ToolCallStatus.SUCCESS,
                latency_ms=50.0,
            )
        ]
    )


@pytest.fixture
def mock_vector_store(
    sample_retrieval_result,
):
    """Return an AsyncMock VectorStoreInterface returning canned results."""
    store = AsyncMock()
    store.retrieve.return_value = sample_retrieval_result
    store.health_check.return_value = True
    return store


@pytest.fixture
def mock_llm_provider(
    sample_generation_result,
):
    """Return an AsyncMock LLMProviderInterface returning canned results."""
    provider = AsyncMock()
    provider.generate.return_value = sample_generation_result
    provider.health_check.return_value = True
    return provider


@pytest.fixture
def mock_mcp_client(
    sample_tool_chain,
):
    """Return an AsyncMock MCPClientInterface returning a canned tool call result."""
    client = AsyncMock()
    client.call_tool.return_value = sample_tool_chain.calls[0]
    client.health_check.return_value = True
    return client


@pytest.fixture
def mock_tracer():
    """Return a mock TracerInterface whose spans are no-ops.

    TracerInterface.start_span is a SYNCHRONOUS method that returns an
    async context manager (it is not itself a coroutine — only the
    context manager's __aenter__/__aexit__ are async). Using a plain
    AsyncMock for the whole tracer would make start_span(...) return a
    coroutine instead of a context manager, breaking `async with
    tracer.start_span(...)`. So the tracer is a MagicMock (sync by
    default) with only get_trace_url overridden to be async, matching
    the real interface's method signatures.
    """
    tracer = MagicMock()

    class _NullSpan:
        """A no-op async context manager standing in for a real span."""

        async def __aenter__(self):
            """Return self; no span actually starts."""
            return self

        async def __aexit__(self, *args):
            """No-op; no span actually ends."""
            return False

        def set_attribute(self, *args, **kwargs):
            """No-op attribute setter."""
            pass

    tracer.start_span.return_value = _NullSpan()
    tracer.get_trace_url = AsyncMock(return_value=None)
    tracer.get_current_trace_id = MagicMock(return_value=None)
    return tracer


@pytest.fixture
def mock_evaluator(
    sample_eval_score,
):
    """Return an AsyncMock EvaluatorInterface returning a canned score."""
    evaluator = AsyncMock()
    evaluator.score.return_value = sample_eval_score
    return evaluator


@pytest.fixture
def mock_gateway():
    """Return an AsyncMock GatewayInterface with a canned status response."""
    gateway = AsyncMock()
    gateway.get_status.return_value = {
        "cache_enabled": False,
        "routing_enabled": False,
    }
    return gateway
