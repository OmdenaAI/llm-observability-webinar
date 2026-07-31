"""Scenarios router — one endpoint per demo moment, each delegating to
the corresponding core/scenarios/*.py use case."""
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas.scenario import (
    ContextComparisonResponse,
    ContextSingleTurnResponse,
    CostScenarioResponse,
    QualityTrapResponse,
    ReliabilityScenarioRequest,
    ReliabilityScenarioResponse,
    StaleContextResponse,
    ToolCallDetail,
    TraceabilityScenarioResponse,
)
from src.config.container import Container
from src.core.scenarios.context_scenario import ContextScenario
from src.core.scenarios.cost_scenario import CostScenario
from src.core.scenarios.quality_trap_scenario import QualityTrapScenario
from src.core.scenarios.reliability_scenario import ReliabilityScenario
from src.core.scenarios.traceability_scenario import (
    SPRINT_STATUS_QUESTION,
    TraceabilityScenario,
)
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(
    prefix="/scenarios",
    tags=["Demo Scenarios"],
)


@router.post(
    "/cost",
    response_model=CostScenarioResponse,
)
@inject
async def run_cost_scenario(
    question: str,
    scenario: CostScenario = Depends(Provide[Container.cost_scenario]),
) -> CostScenarioResponse:
    """Run Moment 1 — the question before and after enabling cache + routing.

    Args:
        question: The question to run in both gateway states.
        scenario: Injected cost scenario use case.

    Returns:
        The before/after costs and the computed savings.

    Raises:
        HTTPException: 500 if the scenario fails unexpectedly.
    """
    try:
        result = await scenario.run(question)
        return CostScenarioResponse(
            before_cost_usd=result.before.generation.cost_usd,
            after_cost_usd=result.after.generation.cost_usd,
            cost_delta_usd=result.cost_delta_usd,
            before_cache_hit=result.before.generation.cache_hit,
            after_cache_hit=result.after.generation.cache_hit,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Cost scenario failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Cost scenario failed to run.",
        )


@router.post(
    "/quality-trap",
    response_model=QualityTrapResponse,
)
@inject
async def run_quality_trap_scenario(
    trap_question: str,
    scenario: QualityTrapScenario = Depends(Provide[Container.quality_trap_scenario]),
) -> QualityTrapResponse:
    """Run Moment 2 — forces the high-relevancy/low-faithfulness trap case.

    Args:
        trap_question: The fixed question known to trigger the trap.
        scenario: Injected quality trap scenario use case.

    Returns:
        The answer and its relevancy/faithfulness scores.

    Raises:
        HTTPException: 500 if the scenario fails unexpectedly.
    """
    try:
        result = await scenario.run(trap_question)
        return QualityTrapResponse(
            answer=result.response.answer,
            relevancy=result.eval_score.relevancy,
            faithfulness=result.eval_score.faithfulness,
            is_quality_trap=result.eval_score.is_quality_trap,
            retrieved_sources=[
                chunk.source for chunk in result.response.retrieval.chunks
            ]
            if result.response.retrieval
            else [],
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Quality trap scenario failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Quality trap scenario failed to run.",
        )


@router.post(
    "/context-comparison",
    response_model=ContextComparisonResponse,
)
@inject
async def run_context_comparison(
    question: str,
    scenario: ContextScenario = Depends(Provide[Container.context_scenario]),
) -> ContextComparisonResponse:
    """Run Moment 3, part 1 — plain vs. contextual retrieval comparison.

    Args:
        question: The question to run under both retrieval modes.
        scenario: Injected context scenario use case.

    Returns:
        The faithfulness scores under each mode, plus the delta.

    Raises:
        HTTPException: 500 if the scenario fails unexpectedly.
    """
    try:
        result = await scenario.run_comparison(question)
        return ContextComparisonResponse(
            plain_faithfulness=result.plain_score.faithfulness,
            contextual_faithfulness=result.contextual_score.faithfulness,
            faithfulness_delta=result.faithfulness_delta,
            plain_sources=[chunk.source for chunk in result.plain.retrieval.chunks]
            if result.plain.retrieval
            else [],
            contextual_sources=[
                chunk.source for chunk in result.contextual.retrieval.chunks
            ]
            if result.contextual.retrieval
            else [],
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Context comparison scenario failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Context comparison failed to run.",
        )


@router.post(
    "/context-single",
    response_model=ContextSingleTurnResponse,
)
@inject
async def run_context_single_turn(
    question: str,
    use_contextual_retrieval: bool,
    scenario: ContextScenario = Depends(Provide[Container.context_scenario]),
) -> ContextSingleTurnResponse:
    """Run Moment 3 as a single, interactive turn under one retrieval mode.

    Used by the UI's ask-toggle-ask flow: the presenter asks once with
    contextual retrieval off, sees the score, toggles it on, asks the
    same question again, and sees the score change — as two real,
    separately visible turns rather than one button computing a diff.

    Args:
        question: The question to ask.
        use_contextual_retrieval: Which retrieval mode to use.
        scenario: Injected context scenario use case.

    Returns:
        The answer, its scores, and which retrieval mode actually ran.

    Raises:
        HTTPException: 500 if the scenario fails unexpectedly.
    """
    try:
        result = await scenario.run_single_turn(question, use_contextual_retrieval)
        return ContextSingleTurnResponse(
            answer=result.response.answer,
            relevancy=result.eval_score.relevancy,
            faithfulness=result.eval_score.faithfulness,
            retrieval_mode=result.response.retrieval.retrieval_mode
            if result.response.retrieval
            else "unknown",
            trace_url=result.response.trace_url,
            retrieved_sources=[
                chunk.source for chunk in result.response.retrieval.chunks
            ]
            if result.response.retrieval
            else [],
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Context single-turn scenario failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Context single-turn scenario failed to run.",
        )


@router.post(
    "/stale-context",
    response_model=StaleContextResponse,
)
@inject
async def run_stale_context_case(
    stale_question: str,
    scenario: ContextScenario = Depends(Provide[Container.context_scenario]),
) -> StaleContextResponse:
    """Run Moment 3, part 2 — the stale-context failure mode.

    Args:
        stale_question: The fixed question known to retrieve the
            deliberately outdated document.
        scenario: Injected context scenario use case.

    Returns:
        The answer, its faithfulness score, and whether it exhibits the
        "passes eval but wrong" pattern.

    Raises:
        HTTPException: 500 if the scenario fails unexpectedly.
    """
    try:
        result = await scenario.run_stale_context_case(stale_question)
        return StaleContextResponse(
            answer=result.response.answer,
            faithfulness=result.eval_score.faithfulness,
            passes_eval_but_wrong=result.passes_eval_but_wrong,
            retrieved_sources=[
                chunk.source for chunk in result.response.retrieval.chunks
            ]
            if result.response.retrieval
            else [],
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Stale context scenario failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Stale context scenario failed to run.",
        )


@router.post(
    "/reliability",
    response_model=ReliabilityScenarioResponse,
)
@inject
async def run_reliability_scenario(
    payload: ReliabilityScenarioRequest,
    scenario: ReliabilityScenario = Depends(Provide[Container.reliability_scenario]),
) -> ReliabilityScenarioResponse:
    """Run Moment 4 — call this AFTER the provider has been killed.

    The provider must already be down (e.g. via `make kill-provider`)
    before calling this endpoint — it does not trigger the outage itself.

    Args:
        payload: The question to ask post-outage.
        scenario: Injected reliability scenario use case.

    Returns:
        The answer, plus whether a failover path was used.

    Raises:
        HTTPException: 500 if the scenario fails unexpectedly.
    """
    try:
        result = await scenario.run_after_outage(payload.question)
        return ReliabilityScenarioResponse(
            answer=result.response.answer,
            failed_over=result.failed_over,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Reliability scenario failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Reliability scenario failed to run.",
        )


@router.post(
    "/traceability",
    response_model=TraceabilityScenarioResponse,
)
@inject
async def run_traceability_scenario(
    scenario: TraceabilityScenario = Depends(Provide[Container.traceability_scenario]),
) -> TraceabilityScenarioResponse:
    """Run Moment 5 — the fixed sprint-status question.

    Chains four read-only MCP calls to Umaku: sprints_get_active,
    kanban_get_board, projects_get_dashboard, and
    performance_assessments_by_project.

    Args:
        scenario: Injected traceability scenario use case.

    Returns:
        The answer, the number of tool calls made, whether they all
        succeeded, and a link to the trace.

    Raises:
        HTTPException: 500 if the scenario fails unexpectedly.
    """
    try:
        result = await scenario.run(SPRINT_STATUS_QUESTION)
        return TraceabilityScenarioResponse(
            answer=result.response.answer,
            tool_call_count=result.tool_call_count,
            all_calls_succeeded=result.all_calls_succeeded,
            tool_calls=[
                ToolCallDetail(
                    tool_name=call.tool_name,
                    status=call.status.value,
                    latency_ms=call.latency_ms,
                    error_message=call.error_message,
                )
                for call in result.calls
            ],
            trace_url=result.response.trace_url,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Traceability scenario failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Traceability scenario failed to run.",
        )