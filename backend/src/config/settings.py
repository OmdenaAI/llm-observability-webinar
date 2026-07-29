from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables and .env.

    Fields are grouped by the external service/provider they configure,
    matching the layout of infra/*.yaml and docker-compose.yml. Fields
    that select between swappable backends (e.g. `vector_store_backend`,
    `llm_provider`) are read by src/config/container.py to decide which
    concrete infrastructure implementation to bind.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "LLM Observability Demo"
    app_version: str = "0.1.0"
    app_environment: Literal["development", "test", "production"] = "development"
    debug: bool = False

    cors_origins_raw: str = Field(default="http://localhost:5173", alias="cors_origins")

    # --- Vector store -------------------------------------------------------
    vector_store_backend: Literal["qdrant", "pgvector", "chroma"] = "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "demo_corpus"
    pgvector_dsn: str = "postgresql://localhost:5432/vectordb"
    # Embeddings for ingestion + retrieval. OpenAI is the only embedding
    # provider wired up currently — reuses OPENAI_API_KEY from the Evals
    # section below, since both are "OpenAI doing a well-understood job."
    openai_embedding_model: str = "text-embedding-3-small"

    # --- LLM / gateway --------------------------------------------------------
    llm_provider: Literal["ollama", "litellm"] = "litellm"
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2:1b"
    litellm_gateway_url: str = "http://localhost:4000"
    litellm_default_model: str = "primary-model"
    litellm_admin_api_key: str = Field(default="", alias="LITELLM_ADMIN_API_KEY")
    gateway_cache_enabled_default: bool = False
    gateway_routing_enabled_default: bool = False
    # Fallback chain for Moment 4 (live provider outage). The primary model
    # is local Ollama, which the demo kills on stage; fallbacks are real
    # hosted providers so the failover is genuine, not another local call.
    # Reuses the same OPENAI_API_KEY / ANTHROPIC_API_KEY as the eval judge
    # settings below, since both are "a real hosted model used as a backup
    # brain" — one for grading answers, one for answering them.
    litellm_fallback_model_openai: str = "gpt-4o-mini"
    litellm_fallback_model_anthropic: str = "claude-3-5-sonnet-latest"

    # --- MCP / Umaku ----------------------------------------------------------
    umaku_mcp_url: str = "https://mcp.umaku.ai/mcp"
    umaku_mcp_token: str = Field(default="", alias="UMAKU_MCP_TOKEN")
    # Required by every project-scoped Umaku tool this demo calls
    # (sprints_get_active, kanban_get_board, projects_get_dashboard,
    # performance_assessments_by_project) — confirmed via a live curl
    # test, which returned a validation error without it. Find this in
    # the Umaku platform UI, in the dedicated demo project's URL/settings.
    umaku_project_id: str = Field(default="", alias="UMAKU_PROJECT_ID")

    # --- Observability backend --------------------------------------------------
    observability_backend: Literal["langfuse", "phoenix"] = "langfuse"
    otel_collector_endpoint: str = "http://localhost:4318"
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = "https://cloud.langfuse.com"
    # Two separate values are needed here: the backend container exports
    # traces to Phoenix over Docker's internal network (service name
    # "phoenix"), while trace_url links shown to the presenter need the
    # host-mapped address their browser can actually reach. Using one
    # value for both was a real bug — "localhost" inside the backend
    # container refers to the container itself, not the Phoenix
    # container, so exports would have silently gone nowhere.
    phoenix_internal_host: str = "http://phoenix:6006"
    phoenix_host: str = "http://localhost:6006"

    # --- Evals ------------------------------------------------------------------
    ragas_enabled: bool = True
    deepeval_enabled: bool = True
    # Judge LLM used by RAGAS/DeepEval to score faithfulness/relevancy.
    # "openai" is the default since both libraries' built-in metrics are
    # most battle-tested against it; "anthropic" is supported as an
    # alternate judge for teams that prefer to keep the judge model
    # consistent with a Claude-based stack, or to avoid an OpenAI dependency.
    eval_judge_provider: Literal["openai", "anthropic"] = "openai"
    eval_judge_model: str = "gpt-4o-mini"  # e.g. "claude-3-5-sonnet-latest" if anthropic
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # --- Seed data ----------------------------------------------------------------
    corpus_path: str = str(PROJECT_ROOT / "data" / "corpus")

    @property
    def cors_origins(
        self,
    ) -> list[str]:
        """Parse the comma-separated CORS origins env value into a list.

        Stored as a raw string (not list[str]) because pydantic-settings
        tries to JSON-decode list-typed env values before field
        validators run, which breaks on a simple comma-separated string.
        """
        return [
            item.strip()
            for item in self.cors_origins_raw.split(",")
            if item.strip()
        ]

    @property
    def vector_store_url(
        self,
    ) -> str:
        """Return the connection URL for the currently configured vector store backend.

        Raises:
            ValueError: If `vector_store_backend` is set to a backend
                without a corresponding URL field (e.g. "chroma", which
                has no dedicated connection field yet).
        """
        if self.vector_store_backend == "qdrant":
            return self.qdrant_url
        if self.vector_store_backend == "pgvector":
            return self.pgvector_dsn
        raise ValueError(
            f"Unsupported vector_store_backend: {self.vector_store_backend}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return the cached, process-wide Settings instance.

    Cached via lru_cache so settings are parsed from the environment
    exactly once per process, rather than on every access.
    """
    return Settings()
