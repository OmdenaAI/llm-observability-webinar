"""LLM-as-judge evaluator, scoring faithfulness and relevancy.

Named "Ragas" for continuity with the workshop doc's terminology and
Moments 2/3 of the demo — but does NOT depend on the `ragas` PyPI
package. As of this writing, ragas>=0.2 unconditionally imports
`langchain_community.chat_models.vertexai`, which no longer exists in
current langchain-community releases; pinning an older
langchain-community to work around that then requires a LangChain v0.3
core, which conflicts with langchain-openai/langchain-anthropic's
LangChain v1.0 requirement. Both were verified to actually fail during
implementation — not a hypothetical concern.

Rather than pin the whole project to a legacy LangChain version for one
evaluator, this implements the same "LLM judges faithfulness and
relevancy" methodology directly against the OpenAI/Anthropic SDKs. This
is also arguably better suited to a live demo: fewer dependency layers
between "ask the judge" and "get a score" means fewer things that can
break on stage.

Judge model is configurable — OpenAI (default) or Anthropic — set via
EVAL_JUDGE_PROVIDER / EVAL_JUDGE_MODEL in settings.
"""
import json

from src.domain.entities.eval_score import EvalScore
from src.domain.entities.query import RetrievedChunk
from src.infrastructure.evals.base import BaseEvaluator
from utils.logger import get_logger

logger = get_logger()

# Single combined judge call scoring both faithfulness and relevancy at
# once — fewer round trips than two separate calls, which matters for a
# metric that needs to run synchronously inside a live demo request.
JUDGE_SYSTEM_PROMPT = """You are a strict evaluator of AI-generated answers. \
Given a question, retrieved context, and a generated answer, score two \
things on a 0.0-1.0 scale:

- "faithfulness": how well the answer is grounded in the retrieved context. \
A 1.0 means every claim in the answer is directly supported by the \
context. A 0.0 means the answer is entirely unsupported or contradicts \
the context. If the answer states something the context does not \
contain, that portion is unfaithful even if it sounds plausible.

- "relevancy": how directly the answer addresses the question asked, \
regardless of whether it is grounded in the context. A 1.0 means the \
answer is squarely on-topic. A 0.0 means the answer does not address \
the question at all.

Respond with ONLY a JSON object of the exact form:
{"faithfulness": <float>, "relevancy": <float>, "reasoning": "<one \
sentence explaining the faithfulness score specifically>"}"""


def _build_judge_user_prompt(
    question: str,
    answer: str,
    context: list[RetrievedChunk],
) -> str:
    """Assemble the user-turn prompt sent to the judge model.

    Args:
        question: The original question asked.
        answer: The generated answer to evaluate.
        context: The chunks the answer should be grounded in.

    Returns:
        The formatted prompt string.
    """
    context_block = (
        "\n\n".join(chunk.content for chunk in context)
        if context
        else "(no context was retrieved)"
    )
    return (
        f"Question:\n{question}\n\n"
        f"Retrieved context:\n{context_block}\n\n"
        f"Generated answer:\n{answer}"
    )


def _parse_judge_response(
    raw_text: str,
) -> tuple[float, float]:
    """Parse the judge's JSON response into (faithfulness, relevancy).

    Tolerates the model wrapping its JSON in markdown code fences, since
    not every provider reliably honors "respond with only JSON."

    Args:
        raw_text: The raw text returned by the judge model.

    Returns:
        A (faithfulness, relevancy) tuple.

    Raises:
        ValueError: If the response cannot be parsed as the expected JSON shape.
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        return float(data["faithfulness"]), float(data["relevancy"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"Judge response was not the expected JSON shape: {raw_text!r}"
        ) from exc


class RagasEvaluator(BaseEvaluator):
    """LLM-as-judge evaluator scoring faithfulness and relevancy directly."""

    def __init__(
        self,
        judge_provider: str = "openai",
        judge_model: str = "gpt-4o-mini",
        openai_api_key: str = "",
        anthropic_api_key: str = "",
    ) -> None:
        """Initialize the evaluator's judge client.

        Args:
            judge_provider: Which provider to use as the judge —
                "openai" or "anthropic".
            judge_model: The specific model name to use as the judge
                (e.g. "gpt-4o-mini" or "claude-3-5-sonnet-latest").
            openai_api_key: API key used if judge_provider is "openai".
            anthropic_api_key: API key used if judge_provider is
                "anthropic".

        Raises:
            ValueError: If judge_provider is not "openai" or "anthropic".
        """
        self._judge_provider = judge_provider
        self._judge_model = judge_model

        if judge_provider == "openai":
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=openai_api_key)
        elif judge_provider == "anthropic":
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=anthropic_api_key)
        else:
            raise ValueError(
                f"Unsupported eval_judge_provider: {judge_provider!r}. "
                "Expected 'openai' or 'anthropic'."
            )

    async def _call_judge(
        self,
        user_prompt: str,
    ) -> str:
        """Call the configured judge model and return its raw text response.

        Args:
            user_prompt: The assembled question/context/answer prompt.

        Returns:
            The judge's raw text response, expected to be JSON.
        """
        if self._judge_provider == "openai":
            response = await self._client.chat.completions.create(
                model=self._judge_model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content

        # Anthropic has no strict JSON response_format; the system prompt's
        # "respond with ONLY a JSON object" instruction plus
        # _parse_judge_response's fence-stripping cover the common cases.
        response = await self._client.messages.create(
            model=self._judge_model,
            max_tokens=300,
            temperature=0,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.content[0].text

    async def _do_score(
        self,
        question: str,
        answer: str,
        context: list[RetrievedChunk],
    ) -> EvalScore:
        """Score an answer for faithfulness and relevancy via the judge model.

        Args:
            question: The original question asked.
            answer: The generated answer to evaluate.
            context: The chunks the answer should be grounded in.

        Returns:
            The relevancy/faithfulness scores for this triple.
        """
        user_prompt = _build_judge_user_prompt(question, answer, context)
        raw_response = await self._call_judge(user_prompt)
        faithfulness, relevancy = _parse_judge_response(raw_response)

        # TEMPORARY diagnostic logging — remove once Moment 2/3 scoring
        # behavior is confirmed stable. INFO level so it's visible
        # without changing the backend's configured log level.
        try:
            reasoning = json.loads(
                raw_response.strip().strip("`").removeprefix("json").strip()
            ).get("reasoning", "<no reasoning field>")
        except (json.JSONDecodeError, AttributeError):
            reasoning = "<could not parse reasoning from judge response>"
        logger.info(
            f"Judge scores — faithfulness={faithfulness:.3f}, "
            f"relevancy={relevancy:.3f} | reasoning: {reasoning} | "
            f"context sources: {[c.source for c in context]} | "
            f"answer: {answer[:200]!r}"
        )

        return EvalScore(
            relevancy=relevancy,
            faithfulness=faithfulness,
            evaluator_name=f"llm-judge-{self._judge_provider}",
        )