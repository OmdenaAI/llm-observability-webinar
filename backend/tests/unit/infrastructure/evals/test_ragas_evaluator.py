"""Unit tests for RagasEvaluator (the LLM-as-judge implementation).

Construction is real — building the OpenAI/Anthropic SDK client
requires no network call, just a key string — but `_call_judge` is
mocked so this suite never hits a real provider API.
"""
import json
from unittest.mock import AsyncMock

from src.infrastructure.evals.ragas_evaluator import (
    RagasEvaluator,
    _build_judge_user_prompt,
    _parse_judge_response,
)


def _build_evaluator_with_mocked_judge(
    faithfulness_value: float,
    relevancy_value: float,
) -> RagasEvaluator:
    """Construct a real RagasEvaluator with `_call_judge` mocked to
    return a fixed, well-formed JSON judge response.

    Args:
        faithfulness_value: The faithfulness score the mocked judge
            call should return.
        relevancy_value: The relevancy score the mocked judge call
            should return.

    Returns:
        A RagasEvaluator whose _do_score will return the given values.
    """
    evaluator = RagasEvaluator(
        judge_provider="openai",
        judge_model="gpt-4o-mini",
        openai_api_key="test-key-not-a-real-key",
    )
    fake_response = json.dumps(
        {
            "faithfulness": faithfulness_value,
            "relevancy": relevancy_value,
            "reasoning": "test reasoning",
        }
    )
    evaluator._call_judge = AsyncMock(return_value=fake_response)
    return evaluator


async def test_do_score_maps_judge_output_to_eval_score(
    sample_chunk,
):
    """_do_score should map the judge's raw JSON output onto EvalScore fields."""
    evaluator = _build_evaluator_with_mocked_judge(
        faithfulness_value=0.42,
        relevancy_value=0.91,
    )

    result = await evaluator._do_score(
        question="How long is data retained?",
        answer="Data is retained for 90 days.",
        context=[sample_chunk],
    )

    assert result.faithfulness == 0.42
    assert result.relevancy == 0.91
    assert result.evaluator_name == "llm-judge-openai"


async def test_do_score_detects_quality_trap_pattern(
    sample_chunk,
):
    """High relevancy + low faithfulness should be flagged as a quality trap."""
    evaluator = _build_evaluator_with_mocked_judge(
        faithfulness_value=0.3,
        relevancy_value=0.85,
    )

    result = await evaluator._do_score(
        question="How long is data retained?",
        answer="Data is retained for exactly 90 days.",
        context=[sample_chunk],
    )

    assert result.is_quality_trap is True


def test_unsupported_judge_provider_raises():
    """An unrecognized judge_provider should fail fast at construction time."""
    try:
        RagasEvaluator(
            judge_provider="not-a-real-provider",
            openai_api_key="test-key",
        )
        assert False, "Expected ValueError for unsupported judge_provider"
    except ValueError as exc:
        assert "not-a-real-provider" in str(exc)


def test_parse_judge_response_handles_plain_json():
    """Plain JSON responses should parse without any cleanup needed."""
    faithfulness, relevancy = _parse_judge_response(
        '{"faithfulness": 0.3, "relevancy": 0.85, "reasoning": "x"}'
    )
    assert faithfulness == 0.3
    assert relevancy == 0.85


def test_parse_judge_response_handles_markdown_fenced_json():
    """Responses wrapped in ```json fences should still parse correctly."""
    faithfulness, relevancy = _parse_judge_response(
        '```json\n{"faithfulness": 0.9, "relevancy": 0.95}\n```'
    )
    assert faithfulness == 0.9
    assert relevancy == 0.95


def test_parse_judge_response_raises_on_malformed_output():
    """Non-JSON judge output should raise ValueError, not fail silently."""
    try:
        _parse_judge_response("The faithfulness score is pretty good, I'd say 0.8")
        assert False, "Expected ValueError for malformed judge output"
    except ValueError:
        pass


def test_build_judge_user_prompt_handles_empty_context(
    sample_chunk,
):
    """An empty context list should still produce a valid, parseable prompt."""
    prompt = _build_judge_user_prompt(
        question="What is X?",
        answer="X is Y.",
        context=[],
    )
    assert "no context was retrieved" in prompt
    assert "What is X?" in prompt
