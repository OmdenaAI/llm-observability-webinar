"""Chat router — the general-purpose RAG endpoint used by the frontend's
ChatWindow component."""
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas.chat import ChatRequest, ChatResponse
from src.config.container import Container
from src.core.rag_orchestrator import RAGOrchestrator
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post(
    "/",
    response_model=ChatResponse,
)
@inject
async def chat(
    payload: ChatRequest,
    orchestrator: RAGOrchestrator = Depends(Provide[Container.rag_orchestrator]),
) -> ChatResponse:
    """Answer a question, optionally chaining MCP tool calls.

    This is the general entrypoint the frontend calls for any question —
    including the fixed sprint-status question, which the orchestrator's
    internal ToolRouter recognizes and expands into the Moment 5 tool
    chain automatically.

    Args:
        payload: The question and retrieval-mode preference.
        orchestrator: Injected RAG orchestrator.

    Returns:
        The generated answer, plus cost/latency/tool-call metadata.

    Raises:
        HTTPException: 500 if the orchestrator fails unexpectedly.
    """
    try:
        response = await orchestrator.handle_question(
            question=payload.question,
            use_contextual_retrieval=payload.use_contextual_retrieval,
        )
        return ChatResponse(
            answer=response.answer,
            model_used=response.generation.model_used,
            cost_usd=response.generation.cost_usd,
            latency_ms=response.generation.latency_ms,
            cache_hit=response.generation.cache_hit,
            tool_calls=[
                call.tool_name for call in response.tool_chain.calls
            ]
            if response.tool_chain
            else [],
            trace_url=response.trace_url,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Error handling chat request: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Unable to process the question, please try again.",
        )
