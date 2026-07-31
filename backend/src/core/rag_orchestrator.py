"""End-to-end orchestration: retrieve -> generate -> optionally call tools.

This is the single place that composes the domain interfaces into a
request flow. Individual demo moments (core/scenarios/*) call into this
rather than reimplementing the flow themselves.
"""
from dataclasses import dataclass, field

import json

from src.core.tool_router import ToolRouter
from src.domain.entities.generation import GenerationResult
from src.domain.entities.query import Query, RetrievalResult, RetrievedChunk
from src.domain.entities.tool_call import ToolCallResult, ToolCallStatus, ToolChain
from src.domain.entities.trace_span import SpanKind
from src.domain.interfaces.llm_provider import LLMProviderInterface
from src.domain.interfaces.mcp_client import MCPClientInterface
from src.domain.interfaces.tracer import TracerInterface
from src.domain.interfaces.vector_store import VectorStoreInterface

# Umaku's exact field name for a sprint's ID within a sprint object,
# and its type, are now confirmed via a live call: the first result's
# "id" key, returned as an INTEGER (e.g. 1467), not a string. Kept as a
# candidate list (checked in order) as defensive fallback in case a
# different Umaku endpoint/version ever shapes this differently, but
# "id" is expected to match on the first try going forward.
_SPRINT_ID_CANDIDATE_KEYS = ("id", "sprint_id", "_id")


def _extract_active_sprint_id(
    sprints_get_active_result: dict | None,
) -> int | str | None:
    """Pull the active sprint's ID out of sprints_get_active's raw result.

    Needed because kanban_get_board requires sprint_ids explicitly — it
    does not default to the active sprint (confirmed in Umaku's
    troubleshooting docs) — so the orchestrator must thread the ID from
    one tool call's result into the next call's arguments.

    Confirmed via a live call that the result is wrapped in a
    {"results": [...], "count": N} envelope, and that the ID itself is
    an integer (e.g. 1467) under the "id" key of the first result item.

    Args:
        sprints_get_active_result: The raw result dict from calling
            sprints_get_active, or None if that call failed.

    Returns:
        The active sprint's ID (typically an int), or None if there is
        no active sprint (empty results) or the result couldn't be parsed.
    """
    if not sprints_get_active_result:
        return None

    results = sprints_get_active_result.get("results")
    if not results:
        # A well-formed, empty response — no active sprint exists for
        # this project. Not an error; the caller should treat this as
        # "no sprint ID available" rather than raise.
        return None

    active_sprint = results[0]
    for key in _SPRINT_ID_CANDIDATE_KEYS:
        if key in active_sprint:
            return active_sprint[key]

    raise KeyError(
        f"sprints_get_active's first result had none of "
        f"{_SPRINT_ID_CANDIDATE_KEYS} as keys — update "
        f"_SPRINT_ID_CANDIDATE_KEYS once the real sprint object shape is known. "
        f"Keys present: {list(active_sprint.keys())}"
    )


def _tool_chain_to_context_chunks(
    tool_chain: ToolChain | None,
) -> list[RetrievedChunk]:
    """Convert successful MCP tool call results into RetrievedChunks.

    This is what actually makes tool results visible to the generator:
    without this, MCP tools could be called and traced successfully
    (Moment 5's spans would all look correct) while the generated
    answer remained entirely ignorant of what they returned, since
    LLMProviderInterface.generate only ever reads from `context`.

    Failed calls are deliberately excluded rather than surfaced as
    context — a failed tool call has no data to ground an answer in,
    and including error text as "context" risks the model treating the
    failure message as answerable content. A failed chain simply
    results in less context, the same way a retrieval miss would.

    Args:
        tool_chain: The tool calls made for this question, or None if
            none were needed.

    Returns:
        One RetrievedChunk per successful tool call, with its raw
        result JSON-serialized as the chunk's content.
    """
    if not tool_chain:
        return []

    chunks = []
    for call in tool_chain.calls:
        if call.status != ToolCallStatus.SUCCESS or call.result is None:
            continue
        chunks.append(
            RetrievedChunk(
                content=json.dumps(call.result, default=str),
                source=f"mcp:{call.tool_name}",
                score=1.0,
                metadata={"tool_call": True, "tool_name": call.tool_name},
            )
        )
    return chunks


@dataclass
class RAGResponse:
    """The full result of handling one user question.

    Everything the chat UI and demo scenarios need to display.

    Attributes:
        answer: The final generated answer text.
        retrieval: The retrieval result used to ground the answer, or
            None if retrieval was skipped.
        generation: The generation result, including cost/latency.
        tool_chain: The MCP tool calls made while answering, or None if
            no tools were needed.
        trace_url: A link to this request's trace in the observability
            backend, if available.
        metadata: Any additional response-level data.
    """

    answer: str
    retrieval: RetrievalResult | None
    generation: GenerationResult
    tool_chain: ToolChain | None
    trace_url: str | None = None
    metadata: dict = field(default_factory=dict)


class RAGOrchestrator:
    """Composes retrieval, generation, and MCP tool calls for one question.

    Depends only on domain interfaces — no infrastructure or
    provider-specific code lives here. Swapping Qdrant for Chroma, or
    Ollama for a hosted provider, never requires touching this class.
    """

    def __init__(
        self,
        vector_store: VectorStoreInterface,
        llm_provider: LLMProviderInterface,
        mcp_client: MCPClientInterface,
        tracer: TracerInterface,
        umaku_project_id: str = "",
    ) -> None:
        """Initialize the orchestrator with its dependencies.

        Args:
            vector_store: Used to retrieve context for a question.
            llm_provider: Used to generate an answer from that context.
            mcp_client: Used to call external tools (e.g. Umaku) when a
                question requires them.
            tracer: Used to record spans for each step of the request.
            umaku_project_id: The Umaku project ID injected into every
                MCP tool call — required by every project-scoped Umaku
                tool this demo calls (confirmed via a live curl test
                against sprints_get_active, which errors without it).
        """
        self._vector_store = vector_store
        self._llm_provider = llm_provider
        self._tool_router = ToolRouter(mcp_client, project_id=umaku_project_id)
        self._mcp_client = mcp_client
        self._tracer = tracer

    async def handle_question(
        self,
        question: str,
        use_contextual_retrieval: bool = False,
        model: str | None = None,
        top_k: int = 2,
    ) -> RAGResponse:
        """Answer a single question end to end.

        Wraps the whole retrieve/generate/tool-call flow in one root
        span, so every child span (retrieve, generate, mcp:*) shares a
        single trace — this is what lets Moment 6's dashboard tie cost,
        quality, and traceability signals back to one request. The root
        span's trace ID is used to populate `trace_url` on the response.

        Args:
            question: The user's natural-language question.
            use_contextual_retrieval: Whether to use the contextual
                retrieval strategy instead of plain retrieval. See
                Moment 3 of the demo.
            model: An optional explicit model override, bypassing the
                LLM provider's own routing policy. Used by
                ReliabilityScenario (Moment 4) to force targeting the
                specific model that was killed — without this, the
                request would follow whatever cache/routing state was
                left over from testing other moments, which could mean
                it never actually hits the dead provider at all.
            top_k: How many retrieved chunks to hand to the generator.
                Defaults to 2 (unchanged behavior for every existing
                caller that doesn't pass this explicitly). Used by
                QualityTrapScenario (Moment 2) with top_k=1, so a
                chunked trap document's disambiguating chunk is excluded
                from context rather than retrieved alongside the
                narrower one — without this override, chunking alone
                doesn't isolate anything, since both chunks would still
                reach the generator together at the default of 2.

        Returns:
            The full response, including retrieval, generation, any
            tool calls made along the way, and a link to this request's
            trace if the tracer backend is configured for one.
        """
        async with self._tracer.start_span(
            name="handle_question",
            kind=SpanKind.REQUEST,
            attributes={"question": question},
        ):
            tool_chain = await self._maybe_call_tools(question)

            retrieval = await self._retrieve(
                question,
                use_contextual_retrieval,
                top_k,
            )

            generation = await self._generate(
                question,
                retrieval,
                tool_chain,
                model,
            )

            trace_id = self._tracer.get_current_trace_id()
            trace_url = (
                await self._tracer.get_trace_url(trace_id) if trace_id else None
            )

            return RAGResponse(
                answer=generation.answer,
                retrieval=retrieval,
                generation=generation,
                tool_chain=tool_chain,
                trace_url=trace_url,
            )

    async def _maybe_call_tools(
        self,
        question: str,
    ) -> ToolChain | None:
        """Call the MCP tool chain for this question, if one is required.

        Special-cases kanban_get_board: Umaku's docs confirm it requires
        an explicit `sprint_ids` argument and never defaults to the
        active sprint, so this threads the ID from sprints_get_active's
        result into kanban_get_board's arguments dynamically, rather
        than relying on the static chain in ToolRouter.

        Args:
            question: The user's natural-language question.

        Returns:
            The results of the tool chain, or None if no tools were
            needed for this question.
        """
        tool_chain_spec = self._tool_router.get_tool_chain(question)
        if not tool_chain_spec:
            return None

        results: list[ToolCallResult] = []
        active_sprint_id: int | str | None = None

        for tool_name, arguments in tool_chain_spec:
            call_arguments = dict(arguments)
            if tool_name == "kanban_get_board" and active_sprint_id is not None:
                # Confirmed via a live curl test: despite the plural name,
                # sprint_ids expects a single STRING, not a JSON array —
                # passing [1467] produced a Pydantic validation error
                # ("Input should be a valid string"). str(active_sprint_id)
                # converts the int ID confirmed in _extract_active_sprint_id
                # into the string form Umaku's API actually wants.
                call_arguments["sprint_ids"] = str(active_sprint_id)

            async with self._tracer.start_span(
                name=f"mcp:{tool_name}",
                kind=SpanKind.TOOL_CALL,
                attributes={"tool_name": tool_name},
            ):
                result = await self._mcp_client.call_tool(
                    tool_name,
                    call_arguments,
                )
                results.append(result)

            if tool_name == "sprints_get_active" and result.status == ToolCallStatus.SUCCESS:
                active_sprint_id = _extract_active_sprint_id(result.result)

        return ToolChain(calls=results)

    async def _retrieve(
        self,
        question: str,
        use_contextual_retrieval: bool,
        top_k: int = 2,
    ) -> RetrievalResult:
        """Retrieve context chunks for the given question.

        Args:
            question: The user's natural-language question.
            use_contextual_retrieval: Whether to use the contextual
                retrieval strategy.
            top_k: How many chunks to retrieve — see handle_question's
                docstring for why this is sometimes overridden.

        Returns:
            The retrieved chunks, wrapped with query and mode metadata.
        """
        query = Query(
            text=question,
            use_contextual_retrieval=use_contextual_retrieval,
        )
        async with self._tracer.start_span(
            name="retrieve",
            kind=SpanKind.RETRIEVAL,
            attributes={"contextual": use_contextual_retrieval, "top_k": top_k},
        ):
            return await self._vector_store.retrieve(query, top_k)

    async def _generate(
        self,
        question: str,
        retrieval: RetrievalResult,
        tool_chain: ToolChain | None,
        model: str | None = None,
    ) -> GenerationResult:
        """Generate an answer from the question, retrieved context, and any
        MCP tool results.

        Tool results are converted to RetrievedChunks and merged with
        retrieval.chunks before calling the LLM provider — without
        this, tool calls would be made and traced (Moment 5's spans
        would look correct) but the generated answer would never
        actually reflect what the tools returned, since
        LLMProviderInterface.generate only reads from `context`.

        Args:
            question: The user's natural-language question.
            retrieval: The retrieval result to ground the answer in.
            tool_chain: The tool calls made for this question, whose
                successful results are folded into the generation
                context alongside retrieved chunks.
            model: An optional explicit model override — see
                handle_question's docstring.

        Returns:
            The generated answer, along with cost/latency metadata.
        """
        tool_context_chunks = _tool_chain_to_context_chunks(tool_chain)
        combined_context = retrieval.chunks + tool_context_chunks

        async with self._tracer.start_span(
            name="generate",
            kind=SpanKind.GENERATION,
            attributes={
                "context_chunks": len(retrieval.chunks),
                "tool_result_chunks": len(tool_context_chunks),
            },
        ) as span:
            generation = await self._llm_provider.generate(
                question=question,
                context=combined_context,
                model=model,
            )

            # Attached AFTER the call, since these values (actual model
            # used, cost, cache hit, whether a fallback fired) are only
            # known once generation completes — not at span-start time.
            # This is what makes cost, model routing, and the Moment 4
            # failover actually visible in Langfuse/Phoenix, rather than
            # only in this app's own UI: without these attributes, a
            # trace shows that a "generate" step happened, but nothing
            # about which model answered or whether it was a fallback.
            span.set_attribute(
                "gen_ai.request.model",
                generation.metadata.get("requested_model") or model or "unknown",
            )
            span.set_attribute("gen_ai.response.model", generation.model_used)
            span.set_attribute("gen_ai.usage.input_tokens", generation.prompt_tokens)
            span.set_attribute(
                "gen_ai.usage.output_tokens", generation.completion_tokens
            )
            span.set_attribute("llm.cost_usd", generation.cost_usd)
            span.set_attribute("llm.cache_hit", generation.cache_hit)
            span.set_attribute(
                "llm.failover_triggered",
                bool(generation.metadata.get("failover_triggered", False)),
            )

            return generation