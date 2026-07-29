"""Unit tests for QualityTrapScenario (Moment 2)."""
from src.core.rag_orchestrator import RAGOrchestrator
from src.core.scenarios.quality_trap_scenario import QualityTrapScenario


async def test_quality_trap_scenario_returns_eval_score(
    mock_vector_store,
    mock_llm_provider,
    mock_mcp_client,
    mock_tracer,
    mock_evaluator,
    mock_gateway,
):
    """Running the scenario should answer the question and score it exactly once."""
    orchestrator = RAGOrchestrator(
        vector_store=mock_vector_store,
        llm_provider=mock_llm_provider,
        mcp_client=mock_mcp_client,
        tracer=mock_tracer,
    )
    scenario = QualityTrapScenario(
        orchestrator=orchestrator,
        evaluator=mock_evaluator,
        gateway=mock_gateway,
    )

    result = await scenario.run("How long is data retained?")

    assert result.eval_score.relevancy == 0.9
    mock_evaluator.score.assert_awaited_once()
    mock_gateway.set_cache_enabled.assert_awaited_once_with(False)


# TODO: add a case where mock_evaluator returns a score with
# is_quality_trap=True (high relevancy, low faithfulness) once the fixture
# supports parametrizing EvalScore per test.
