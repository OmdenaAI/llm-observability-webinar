"""Dependency injection container for application resources and services.

Backend-swappable components (vector store, LLM provider) use
providers.Selector, keyed off settings, so changing `.env` is enough to
swap implementations — no code change, matching the pattern demonstrated
live in the webinar (e.g. swapping Langfuse for Phoenix without
re-instrumenting).
"""
from dependency_injector import containers, providers

from src.config.settings import get_settings
from src.core.rag_orchestrator import RAGOrchestrator
from src.core.scenarios.context_scenario import ContextScenario
from src.core.scenarios.cost_scenario import CostScenario
from src.core.scenarios.quality_trap_scenario import QualityTrapScenario
from src.core.scenarios.reliability_scenario import ReliabilityScenario
from src.core.scenarios.traceability_scenario import TraceabilityScenario
from src.infrastructure.evals.deepeval_evaluator import DeepEvalEvaluator
from src.infrastructure.evals.ragas_evaluator import RagasEvaluator
from src.infrastructure.gateway.litellm_gateway import LiteLLMGateway
from src.infrastructure.llm.litellm_gateway_provider import LiteLLMGatewayProvider
from src.infrastructure.llm.ollama_provider import OllamaProvider
from src.infrastructure.mcp.umaku_client import UmakuMCPClient
from src.infrastructure.services.eval_service import EvalService
from src.infrastructure.services.generation_service import GenerationService
from src.infrastructure.services.retrieval_service import RetrievalService
from src.infrastructure.services.tool_call_service import ToolCallService
from src.infrastructure.tracing.otel_tracer import OTelTracer
from src.infrastructure.vector_store.qdrant_store import QdrantVectorStore


class Container(containers.DeclarativeContainer):
    """Dependency injection container for application resources and services.

    Bindings are grouped by concern (vector store, LLM provider, gateway,
    MCP, tracing, evals) and composed into the core orchestrator, which
    is in turn composed into one Factory per demo scenario. Swappable
    backends use `providers.Selector` keyed off a `providers.Callable`
    reading the relevant `Settings` field, so `.env` alone decides which
    concrete class gets instantiated.
    """

    config = providers.Singleton(get_settings)

    # --- Vector store (swappable via VECTOR_STORE_BACKEND env var) -------------
    qdrant_store = providers.Singleton(
        QdrantVectorStore,
        url=providers.Callable(
            lambda cfg: cfg.qdrant_url,
            config,
        ),
        collection_name=providers.Callable(
            lambda cfg: cfg.qdrant_collection_name,
            config,
        ),
        openai_api_key=providers.Callable(
            lambda cfg: cfg.openai_api_key,
            config,
        ),
        embedding_model=providers.Callable(
            lambda cfg: cfg.openai_embedding_model,
            config,
        ),
    )
    vector_store = providers.Selector(
        providers.Callable(
            lambda cfg: cfg.vector_store_backend,
            config,
        ),
        qdrant=qdrant_store,
        # pgvector=pgvector_store,  # TODO: add once PgvectorStore is implemented
    )
    retrieval_service = providers.Factory(
        RetrievalService,
        vector_store=vector_store,
    )

    # --- Gateway ------------------------------------------------------------------
    # NOTE: the gateway is deliberately a single LiteLLMGateway instance
    # (not swappable) since its config file — infra/litellm-config.yaml —
    # already defines the cross-provider fallback chain (Ollama primary,
    # OpenAI/Anthropic fallback) needed for Moment 4. Defined before the
    # LLM provider section below since litellm_provider needs to share
    # this same instance for cache/routing state.
    gateway = providers.Singleton(
        LiteLLMGateway,
        gateway_url=providers.Callable(
            lambda cfg: cfg.litellm_gateway_url,
            config,
        ),
        admin_api_key=providers.Callable(
            lambda cfg: cfg.litellm_admin_api_key,
            config,
        ),
    )

    # --- LLM provider (swappable via LLM_PROVIDER env var) ----------------------
    ollama_provider = providers.Singleton(
        OllamaProvider,
        base_url=providers.Callable(
            lambda cfg: cfg.ollama_base_url,
            config,
        ),
        default_model=providers.Callable(
            lambda cfg: cfg.ollama_default_model,
            config,
        ),
    )
    litellm_provider = providers.Singleton(
        LiteLLMGatewayProvider,
        gateway_url=providers.Callable(
            lambda cfg: cfg.litellm_gateway_url,
            config,
        ),
        default_model=providers.Callable(
            lambda cfg: cfg.litellm_default_model,
            config,
        ),
        gateway=gateway,
        admin_api_key=providers.Callable(
            lambda cfg: cfg.litellm_admin_api_key,
            config,
        ),
    )
    llm_provider = providers.Selector(
        providers.Callable(
            lambda cfg: cfg.llm_provider,
            config,
        ),
        ollama=ollama_provider,
        litellm=litellm_provider,
    )
    generation_service = providers.Factory(
        GenerationService,
        llm_provider=llm_provider,
    )

    # --- MCP / Umaku ----------------------------------------------------------------
    mcp_client = providers.Singleton(
        UmakuMCPClient,
        mcp_url=providers.Callable(
            lambda cfg: cfg.umaku_mcp_url,
            config,
        ),
        token=providers.Callable(
            lambda cfg: cfg.umaku_mcp_token,
            config,
        ),
    )
    tool_call_service = providers.Factory(
        ToolCallService,
        mcp_client=mcp_client,
    )

    # --- Tracing --------------------------------------------------------------------
    tracer = providers.Singleton(
        OTelTracer,
        collector_endpoint=providers.Callable(
            lambda cfg: cfg.otel_collector_endpoint,
            config,
        ),
        observability_backend=providers.Callable(
            lambda cfg: cfg.observability_backend,
            config,
        ),
        langfuse_host=providers.Callable(
            lambda cfg: cfg.langfuse_host,
            config,
        ),
        phoenix_host=providers.Callable(
            lambda cfg: cfg.phoenix_host,
            config,
        ),
        langfuse_public_key=providers.Callable(
            lambda cfg: cfg.langfuse_public_key,
            config,
        ),
        langfuse_secret_key=providers.Callable(
            lambda cfg: cfg.langfuse_secret_key,
            config,
        ),
        phoenix_internal_host=providers.Callable(
            lambda cfg: cfg.phoenix_internal_host,
            config,
        ),
    )

    # --- Evals ------------------------------------------------------------------------
    # Judge provider/model/keys are shared config, reused for both
    # evaluators below — see settings.py "Evals" section.
    ragas_evaluator = providers.Singleton(
        RagasEvaluator,
        judge_provider=providers.Callable(
            lambda cfg: cfg.eval_judge_provider,
            config,
        ),
        judge_model=providers.Callable(
            lambda cfg: cfg.eval_judge_model,
            config,
        ),
        openai_api_key=providers.Callable(
            lambda cfg: cfg.openai_api_key,
            config,
        ),
        anthropic_api_key=providers.Callable(
            lambda cfg: cfg.anthropic_api_key,
            config,
        ),
    )
    eval_service = providers.Factory(
        EvalService,
        evaluator=ragas_evaluator,
    )

    # DeepEval — constructed for symmetry and CI test usage; not injected
    # into any live scenario (see docs/architecture_plan.md, "DeepEval gap").
    deepeval_evaluator = providers.Singleton(
        DeepEvalEvaluator,
        judge_provider=providers.Callable(
            lambda cfg: cfg.eval_judge_provider,
            config,
        ),
        judge_model=providers.Callable(
            lambda cfg: cfg.eval_judge_model,
            config,
        ),
        openai_api_key=providers.Callable(
            lambda cfg: cfg.openai_api_key,
            config,
        ),
        anthropic_api_key=providers.Callable(
            lambda cfg: cfg.anthropic_api_key,
            config,
        ),
    )

    # --- Core orchestrator ------------------------------------------------------------
    rag_orchestrator = providers.Factory(
        RAGOrchestrator,
        vector_store=retrieval_service,
        llm_provider=generation_service,
        mcp_client=tool_call_service,
        tracer=tracer,
        umaku_project_id=providers.Callable(
            lambda cfg: cfg.umaku_project_id,
            config,
        ),
    )

    # --- Scenarios (one per demo moment) -----------------------------------------------
    cost_scenario = providers.Factory(
        CostScenario,
        orchestrator=rag_orchestrator,
        gateway=gateway,
    )
    quality_trap_scenario = providers.Factory(
        QualityTrapScenario,
        orchestrator=rag_orchestrator,
        evaluator=eval_service,
        gateway=gateway,
    )
    context_scenario = providers.Factory(
        ContextScenario,
        orchestrator=rag_orchestrator,
        evaluator=eval_service,
        gateway=gateway,
    )
    reliability_scenario = providers.Factory(
        ReliabilityScenario,
        orchestrator=rag_orchestrator,
        gateway=gateway,
    )
    traceability_scenario = providers.Factory(
        TraceabilityScenario,
        orchestrator=rag_orchestrator,
        gateway=gateway,
    )
