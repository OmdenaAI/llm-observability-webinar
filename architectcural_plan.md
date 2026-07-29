# Architecture Plan v2 — Clean Architecture + DI


## Stack

- **Backend:** Python — Clean Architecture with Dependency Injection (`dependency_injector`), FastAPI for the API layer
- **Frontend:** React + TypeScript — minimal, but structured 
- **Infra:** Docker Compose for supporting services (Qdrant, Langfuse, OTel Collector, LiteLLM)
- **Orchestration:** Makefile as the single entrypoint for all local dev/demo commands
- **Entrypoints:** each side owns its own — `backend/main.py` (outside `backend/src/`) starts the API and wires the DI container; `frontend/src/main.tsx` mounts the React app. Neither lives at the repo root; the repo root only holds shared orchestration (Makefile, docker-compose, README).

---

## Why Clean Architecture + DI earns its complexity here

This isn't just code hygiene — it's the same idea the webinar supports:

- **Domain interfaces** (e.g., `VectorStoreInterface`, `LLMProviderInterface` `MCPClientInterface`) mean swapping Qdrant for Chroma, or Ollama for a hosted provider, is a container binding change — not a rewrite. That's a literal demonstration of "vendor-neutral instrumentation" applied to the entire stack, not just tracing.
- **Core layer isolation** means the RAG orchestration logic (which is what actually gets demoed) never touches infrastructure details directly — so instrumentation, retries, and provider swaps can change underneath it without touching the use case.
- **The DI container becomes the single source of truth** for "what's plugged in right now" — useful during dry runs, since toggling Moment 1's cache/routing or Moment 3's retrieval mode is a config/binding change, not new code.

One thing to watch: make the container **fail loudly** on a missing or misconfigured binding rather than silently defaulting to `None` — with six live scenarios, a silent misconfiguration is worse than a crash during a dry run.

---

## Proposed file tree

```
llm-observability-demo/
├── README.md
├── Makefile
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── main.py                               # entrypoint — outside src/, starts the FastAPI app + wires the container
│   ├── src/
│   │   ├── domain/                           # interfaces + entities only, no implementation
│   │   │   ├── interfaces/
│   │   │   │   ├── vector_store.py           # VectorStoreInterface
│   │   │   │   ├── llm_provider.py           # LLMProviderInterface
│   │   │   │   ├── mcp_client.py             # MCPClientInterface
│   │   │   │   ├── tracer.py                 # TracerInterface
│   │   │   │   ├── evaluator.py              # EvaluatorInterface
│   │   │   │   └── gateway.py                # GatewayInterface (routing/caching/failover contract)
│   │   │   └── entities/
│   │   │       ├── query.py                  # Query, RetrievalResult
│   │   │       ├── generation.py             # GenerationResult
│   │   │       ├── tool_call.py               # ToolCallResult
│   │   │       └── eval_score.py             # EvalScore (relevancy, faithfulness)
│   │   │
│   │   ├── core/                             # business logic / use cases — depends only on domain
│   │   │   ├── rag_orchestrator.py           # end-to-end: retrieve → generate → optionally call tools
│   │   │   ├── tool_router.py                # decides when to invoke MCP tools
│   │   │   └── scenarios/                    # one use case per demo moment, for clean isolation during dry runs
│   │   │       ├── cost_scenario.py
│   │   │       ├── quality_trap_scenario.py
│   │   │       ├── context_scenario.py
│   │   │       ├── reliability_scenario.py
│   │   │       └── traceability_scenario.py
│   │   │
│   │   ├── infrastructure/
│   │   │   ├── vector_store/
│   │   │   │   ├── base.py                   # abstract base implementing VectorStoreInterface
│   │   │   │   ├── qdrant_store.py
│   │   │   │   └── pgvector_store.py
│   │   │   ├── llm/
│   │   │   │   ├── base.py                   # abstract base implementing LLMProviderInterface
│   │   │   │   ├── ollama_provider.py
│   │   │   │   └── litellm_gateway_provider.py
│   │   │   ├── mcp/
│   │   │   │   ├── base.py                   # abstract base implementing MCPClientInterface
│   │   │   │   └── umaku_client.py
│   │   │   ├── tracing/
│   │   │   │   ├── base.py                   # abstract base implementing TracerInterface
│   │   │   │   └── otel_tracer.py            # OpenLLMetry/OpenInference wrapper
│   │   │   ├── evals/
│   │   │   │   ├── base.py                   # abstract base implementing EvaluatorInterface
│   │   │   │   ├── ragas_evaluator.py
│   │   │   │   └── deepeval_evaluator.py
│   │   │   ├── gateway/
│   │   │   │   ├── base.py                   # abstract base implementing GatewayInterface
│   │   │   │   └── litellm_gateway.py
│   │   │   └── services/                     # orchestration layer over external deps
│   │   │       ├── retrieval_service.py      # wraps vector_store + instrumentation
│   │   │       ├── generation_service.py     # wraps llm provider + instrumentation
│   │   │       ├── tool_call_service.py      # wraps mcp client + instrumentation
│   │   │       └── eval_service.py           # wraps evaluators, runs on-demand scoring
│   │   │
│   │   ├── config/
│   │   │   ├── settings.py                   # env-driven settings (Pydantic BaseSettings)
│   │   │   └── container.py                  # DI container — binds domain interfaces to infra implementations
│   │   │
│   │   └── api/
│   │       ├── routers/
│   │       │   ├── chat.py                   # POST /chat — drives the RAG orchestrator
│   │       │   ├── scenarios.py              # endpoints to trigger/toggle each demo moment
│   │       │   └── admin.py                  # cache/routing toggles, health checks
│   │       └── schemas/
│   │           ├── chat.py
│   │           └── scenario.py
│   │
│   └── tests/
│       ├── unit/                             # mirrors src/ structure — focused on core + infra logic, everything mocked
│       │   ├── core/
│       │   │   ├── test_rag_orchestrator.py
│       │   │   ├── test_tool_router.py
│       │   │   └── scenarios/
│       │   │       ├── test_cost_scenario.py
│       │   │       ├── test_quality_trap_scenario.py
│       │   │       ├── test_context_scenario.py
│       │   │       ├── test_reliability_scenario.py
│       │   │       └── test_traceability_scenario.py
│       │   └── infrastructure/
│       │       ├── vector_store/test_qdrant_store.py
│       │       ├── llm/test_litellm_gateway_provider.py
│       │       ├── mcp/test_umaku_client.py
│       │       ├── tracing/test_otel_tracer.py
│       │       └── evals/test_ragas_evaluator.py
│       │
│       ├── integration/                      # infra implementations against real/local running services
│       │   ├── test_qdrant_integration.py
│       │   ├── test_litellm_gateway_integration.py
│       │   ├── test_umaku_mcp_integration.py
│       │   └── test_otel_export_integration.py
│       │
│       ├── e2e/                              # full request path through the API, hitting real docker-composed services
│       │   ├── test_chat_flow.py
│       │   ├── test_cost_moment.py
│       │   ├── test_quality_trap_moment.py
│       │   ├── test_context_moment.py
│       │   ├── test_reliability_moment.py
│       │   └── test_traceability_moment.py
│       │
│       └── conftest.py                       # shared pytest fixtures + pytest-mock setup
│
├── frontend/                                 # React + TypeScript
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── ChatWindow.tsx
│       │   ├── ToggleControls.tsx            # cache on/off, contextual retrieval on/off
│       │   └── TraceLink.tsx                 # link/embed to Langfuse/Phoenix for the current request
│       ├── api/
│       │   └── client.ts                     # typed client for the backend API
│       └── types/
│           └── index.ts
│
├── data/
│   ├── corpus/
│   │   └── stale_doc_example.md
│   └── ingest.py
│
├── scripts/
│   ├── seed_umaku.md
│   └── kill_provider.sh
│
├── infra/
│   ├── otel-collector-config.yaml
│   └── litellm-config.yaml
│
└── docs/
    ├── demo_runbook.md
    ├── preflight_checklist.md
    └── architecture_plan.md
```

---

## Makefile targets (planned)

| Target | Purpose |
|---|---|
| `make build` | Build all Docker images (backend, frontend, supporting services) |
| `make run` | Run all containers via Docker Compose (assumes already built) |
| `make run-local` | Run backend/frontend locally (non-Docker) against Dockerized supporting services — for faster iteration |
| `make start` | Full path: build → seed data → run — one command from clean checkout to demo-ready |
| `make stop` | Stop all running containers |
| `make down` | Stop and remove containers/volumes |
| `make logs` | Tail logs across all services |
| `make seed` | Load vector store corpus + confirm Umaku workspace data is present |
| `make test` | Run full test suite (unit + integration + e2e) via pytest |
| `make test-unit` | Run only `tests/unit` — fast, fully mocked, no Docker services required |
| `make test-integration` | Run only `tests/integration` — requires supporting services up (`make run` first) |
| `make test-e2e` | Run only `tests/e2e` — requires the full stack up, exercises each demo moment as a real request |
| `make lint` | Run linters/formatters (backend + frontend) |
| `make kill-provider` | Simulate Moment 4 — stop the primary model provider process |
| `make restore-provider` | Reverse of the above, restore normal operation between dry runs |
| `make dry-run` | Convenience target: start everything + open the trace dashboard, for rehearsal |

---

## Decisions (confirmed)

1. **DI library:** `dependency_injector`, Pydantic v2 (`pydantic-settings`), `@lru_cache` singleton `get_settings()` — following the pattern already shared, extended with fields grouped by provider (`vector_store_backend`, `llm_provider`, `mcp_*`, `otel_*`, `langfuse_*`, `gateway_cache_enabled`, `gateway_routing_enabled`) rather than one flat list
2. **Scenario structure:** separate use-case file per demo moment under `core/scenarios/`, but each is a **thin orchestration wrapper** — it composes `rag_orchestrator`, `retrieval_service`, `generation_service`, and `tool_call_service` rather than reimplementing retrieval/generation logic. Shared logic lives once; scenario files just parameterize it per moment, and map 1:1 to sections of the demo script for easy cross-reference during dry runs.
3. **Frontend tooling:** Vite + React + TypeScript
4. **Tests:** `unit/` (mirrors `src/`, mocked, fast), `integration/` (infra implementations against real local services), `e2e/` (full request path per demo moment, against the full Docker-composed stack) — all pytest, with `pytest-mock` for mocking, `conftest.py` for shared fixtures

## Settings field grouping (planned, following the shared pattern)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    app_name: str = "LLM Observability Demo"
    app_environment: Literal["development", "test", "production"] = "development"

    # Vector store — swappable backend, mirrors the sqlite/postgres pattern
    vector_store_backend: Literal["qdrant", "pgvector", "chroma"] = "qdrant"
    qdrant_url: str = "http://localhost:6333"
    pgvector_dsn: str = "postgresql://localhost:5432/vectordb"

    # LLM / gateway
    llm_provider: Literal["ollama", "litellm"] = "litellm"
    ollama_base_url: str = "http://localhost:11434"
    litellm_gateway_url: str = "http://localhost:4000"
    gateway_cache_enabled: bool = False
    gateway_routing_enabled: bool = False

    # MCP / Umaku
    umaku_mcp_url: str = "https://mcp.umaku.ai/mcp"
    umaku_mcp_token: str = Field(default="", alias="UMAKU_MCP_TOKEN")

    # Observability backend
    observability_backend: Literal["langfuse", "phoenix"] = "langfuse"
    otel_collector_endpoint: str = "http://localhost:4318"
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")

    # Evals
    ragas_enabled: bool = True
    deepeval_enabled: bool = True

    @property
    def vector_store_url(self) -> str:
        return self.qdrant_url if self.vector_store_backend == "qdrant" else self.pgvector_dsn


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## The "DeepEval gap"

DeepEval is positioned in the source workshop doc as the *CI/offline* eval gate (pytest-integrated, regression loop), as distinct from RAGAS's *online/live* role (Moments 2 and 3). Because DeepEval's value is running outside the live request path, it's never wired into any of the six demo moments by design — `DeepEvalEvaluator` exists as a scaffolded, interface-compatible class for symmetry and future CI use, but its `_do_score` remains an intentional stub.

## Verifying the Umaku MCP connection manually

Two ways to check what a tool actually returns (useful for confirming
field names like the active sprint's ID key, referenced as
`_SPRINT_ID_CANDIDATE_KEYS` in `rag_orchestrator.py`):

**MCP Inspector (recommended):**
```bash
npx @modelcontextprotocol/inspector
```
Point it at `https://mcp.umaku.ai/mcp` with header
`x-umaku-token: <your token>`, connect, and call any tool interactively
— the raw JSON response is shown directly in the UI.

**Raw curl**, if you want to see the wire protocol. MCP's streamable-HTTP
transport requires an `initialize` handshake first:

```bash
# 1. Initialize — capture the Mcp-Session-Id response header
curl -i -X POST https://mcp.umaku.ai/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "x-umaku-token: mcp_your_token_here" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-06-18",
      "capabilities": {},
      "clientInfo": {"name": "curl-test", "version": "1.0"}
    }
  }'

# 2. Required "initialized" notification
curl -X POST https://mcp.umaku.ai/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "x-umaku-token: mcp_your_token_here" \
  -H "Mcp-Session-Id: <session-id-from-step-1>" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# 3. Call the actual tool
curl -N -X POST https://mcp.umaku.ai/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "x-umaku-token: mcp_your_token_here" \
  -H "Mcp-Session-Id: <session-id-from-step-1>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {"name": "sprints_get_active", "arguments": {}}
  }'
```
The `-N` flag disables curl's output buffering since the response
streams as SSE. Once you see the real field name for the sprint's ID in
the response, update `_SPRINT_ID_CANDIDATE_KEYS` in
`backend/src/core/rag_orchestrator.py` to put that key first.
