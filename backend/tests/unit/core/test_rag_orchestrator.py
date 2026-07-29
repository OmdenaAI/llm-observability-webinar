"""Unit tests for RAGOrchestrator — all dependencies are mocked, so this
never touches Qdrant/LiteLLM/Umaku/OTel."""
from src.core.rag_orchestrator import RAGOrchestrator


async def test_handle_question_without_tools(
    mock_vector_store,
    mock_llm_provider,
    mock_mcp_client,
    mock_tracer,
):
    """A question with no sprint/team keywords should skip the tool chain
    entirely and only touch retrieval + generation."""
    orchestrator = RAGOrchestrator(
        vector_store=mock_vector_store,
        llm_provider=mock_llm_provider,
        mcp_client=mock_mcp_client,
        tracer=mock_tracer,
    )

    response = await orchestrator.handle_question("What is X?")

    assert response.answer == "X is Y."
    assert response.tool_chain is None
    mock_vector_store.retrieve.assert_awaited_once()
    mock_llm_provider.generate.assert_awaited_once()
    mock_mcp_client.call_tool.assert_not_awaited()


async def test_handle_question_with_tool_chain(
    mock_vector_store,
    mock_llm_provider,
    mock_mcp_client,
    mock_tracer,
):
    """The sprint-status question should trigger the full 4-call MCP chain."""
    orchestrator = RAGOrchestrator(
        vector_store=mock_vector_store,
        llm_provider=mock_llm_provider,
        mcp_client=mock_mcp_client,
        tracer=mock_tracer,
    )

    response = await orchestrator.handle_question(
        "How is the current sprint going, and how's the team doing?"
    )

    assert response.tool_chain is not None
    # ToolRouter's SPRINT_STATUS_TOOL_NAMES has 4 entries
    assert mock_mcp_client.call_tool.await_count == 4


async def test_generate_receives_tool_results_in_context(
    mock_vector_store,
    mock_llm_provider,
    mock_mcp_client,
    mock_tracer,
):
    """Tool call results must actually reach the LLM provider's context —
    not just get called and traced. This is the exact gap that was found
    and fixed: tool calls succeeding and appearing in the trace does not
    by itself mean the generated answer reflects what they returned."""
    orchestrator = RAGOrchestrator(
        vector_store=mock_vector_store,
        llm_provider=mock_llm_provider,
        mcp_client=mock_mcp_client,
        tracer=mock_tracer,
    )

    await orchestrator.handle_question(
        "How is the current sprint going, and how's the team doing?"
    )

    # generate() is called with keyword args — inspect what context it received.
    _, call_kwargs = mock_llm_provider.generate.call_args
    received_context = call_kwargs["context"]

    # 1 chunk from mock_vector_store's canned retrieval result, plus 4
    # from the mocked tool chain (one per successful call).
    assert len(received_context) == 1 + 4
    tool_sourced_chunks = [c for c in received_context if c.source.startswith("mcp:")]
    assert len(tool_sourced_chunks) == 4


async def test_handle_question_passes_contextual_retrieval_flag(
    mock_vector_store,
    mock_llm_provider,
    mock_mcp_client,
    mock_tracer,
):
    """The use_contextual_retrieval flag should reach the vector store's
    retrieve() call unchanged, on the Query object it's given."""
    orchestrator = RAGOrchestrator(
        vector_store=mock_vector_store,
        llm_provider=mock_llm_provider,
        mcp_client=mock_mcp_client,
        tracer=mock_tracer,
    )

    await orchestrator.handle_question(
        "What is X?",
        use_contextual_retrieval=True,
    )

    called_query = mock_vector_store.retrieve.call_args.args[0]
    assert called_query.use_contextual_retrieval is True
