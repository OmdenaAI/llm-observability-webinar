# LLM Observability Demo

A RAG application, instrumented end-to-end, built to reliably reproduce six live demo moments for a webinar on LLM observability (cost, quality, context, reliability, traceability, and a unified dashboard).

See `docs/architecture_plan.md` for the full architecture, `docs/demo_runbook.md` for the moment-by-moment live script, and `docs/preflight_checklist.md` before any dry run.

## Running Locally

### Prerequisites
- Docker + Docker Compose
- `make`
- API keys: OpenAI (embeddings + eval judge + LiteLLM fallback), Anthropic (LiteLLM fallback), Umaku MCP token, Langfuse public/secret keys (Langfuse Cloud recommended over self-hosting — see the commented-out service in `docker-compose.yml`)

No local Python or Node install is needed for the commands below — `start`, `seed`, and `test*` all run inside Docker containers built from the same images used at demo time. The one exception is `make run-local` (faster iteration during active development), which intentionally runs on the host — see that section further down.

Ollama itself needs no manual setup either — `docker-compose.yml`'s `ollama` service automatically pulls a small model (`llama3.2:1b` by default, override via `OLLAMA_DEFAULT_MODEL` in `.env`) on first container start, and caches it in the `ollama_data` volume so subsequent starts skip the pull. LiteLLM and the backend both wait on Ollama's healthcheck — which gates on the model actually being present,
not just the server responding — before starting, so there's no window where a request can hit an unpulled model.

### Setup
```bash
git clone <this-repo>
cd llm-observability-webinar
cp .env.example .env
# fill in: OPENAI_API_KEY, ANTHROPIC_API_KEY, UMAKU_MCP_TOKEN,
# LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY
```

### First run
```bash
make start
```
This builds all images, seeds the vector store (`data/ingest.py` — both the plain and contextual collections needed for Moment 3), and brings the full stack up via Docker Compose. First run will take longer since it also pulls/builds images and downloads the Ollama model (a few hundred MB for `llama3.2:1b`) — subsequent starts are much faster since both are cached.

Once up:
- Frontend (operator console): http://localhost:5173
- Backend API docs (FastAPI's auto-generated Swagger UI): http://localhost:8000/docs
- Langfuse: your Langfuse Cloud project URL (or http://localhost:3000 if self-hosting)
- Phoenix: http://localhost:6006
- Qdrant dashboard: http://localhost:6333/dashboard

### Iterating without full Docker rebuilds
```bash
make install     # one-time: local venv + npm install, only for this workflow
make run-local
```
Runs Qdrant, Ollama, LiteLLM, the OTel Collector, and Phoenix in Docker (the supporting services), but runs the backend (`uvicorn --reload`) and frontend (`npm run dev`) directly on your machine — a much faster feedback loop when actively changing backend/frontend code. This is the only workflow in this project that touches your local Python/Node install; `start`/`seed`/`test*` never do.

### Verifying each piece is actually working
```bash
curl http://localhost:8000/admin/health     # backend liveness
curl http://localhost:6333/collections      # Qdrant reachable + collections exist
curl http://localhost:4000/health           # LiteLLM gateway reachable
curl http://localhost:11434/api/tags        # Ollama reachable + models pulled
```
For the Umaku MCP connection specifically, the easiest check is the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) (`npx @modelcontextprotocol/inspector`) — plug in `https://mcp.umaku.ai/mcp` with header `x-umaku-token: <your token>` and call `health_check` interactively. Curl works too, but MCP's
streamable-HTTP transport requires an `initialize` handshake first (capture the `Mcp-Session-Id` response header, include it on subsequent calls) — see `docs/architecture_plan.md` for the full curl sequence if you want to inspect the raw protocol.

### Running the test suite
```bash
make test-unit          # fast, fully mocked, no services required
make test-integration   # requires `make run` first
make test-e2e           # requires the full stack + a seeded Umaku workspace
```

### Before a live dry run
1. `make seed` — re-run if the corpus or contextualization prompt changes
2. Confirm the Umaku workspace is seeded per `scripts/seed_umaku.md`
3. Walk `docs/preflight_checklist.md` in full
4. `make kill-provider` / `make restore-provider` to rehearse Moment 4 specifically

### Stopping / cleaning up
```bash
make stop    # stop containers, keep volumes (fast restart)
make down    # stop + remove containers and volumes (clean slate)
```

## Demo moments at a glance

| Moment | What it shows | Trigger |
|---|---|---|
| 1 — Cost | Cache/routing toggle → cost drop | UI toggle, or `POST /scenarios/cost` |
| 2 — Quality trap | High relevancy, low faithfulness | `POST /scenarios/quality-trap` |
| 3 — Context | Contextual retrieval + stale-context case | `POST /scenarios/context-comparison`, `/scenarios/stale-context` |
| 4 — Reliability | Live provider outage, automatic failover | `make kill-provider`, then `POST /scenarios/reliability` |
| 5 — Traceability | 4 chained, read-only MCP calls to Umaku | `POST /scenarios/traceability`, or ask the sprint-status question in the UI |
| 6 — Dashboard | Unified view across all signals | Open Langfuse/Phoenix directly |

## Architecture (short version)

Clean Architecture + Dependency Injection on the backend:

- `domain/` — interfaces and entities only, no external dependencies
- `core/` — business logic (RAG orchestration, one use case per demo moment)
- `infrastructure/` — concrete implementations (Qdrant, LiteLLM, Umaku MCP, OTel, LLM-as-judge eval), each behind a `base.py` abstract class so backends are swappable via `.env` alone
- `config/` — settings + the DI container wiring everything together
- `api/` — FastAPI routers

Full details, file tree, and open decisions: [architecture_plan.md](architectcural_plan.md).
