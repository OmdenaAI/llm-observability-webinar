# Everything here runs inside Docker — no local Python/Node install is
# required for `start`, `seed`, or `test*`. The only exception is
# `run-local`, which deliberately runs the backend/frontend on the host
# for faster iteration during active development; see its own comment.

.PHONY: install build run run-local start stop down logs seed \
        test test-unit test-integration test-e2e lint \
        kill-provider restore-provider dry-run

# --- Full lifecycle -----------------------------------------------------------

build: ## Build all Docker images (backend, frontend, supporting services)
	docker compose build

run: ## Run all containers via Docker Compose (assumes already built)
	docker compose up -d

start: build seed run ## Full path: build -> seed data -> run — everything in Docker
	@echo "Stack is up. Frontend: http://localhost:5173  Backend: http://localhost:8000"

stop: ## Stop all running containers
	docker compose stop

down: ## Stop and remove containers/volumes
	docker compose down -v

logs: ## Tail logs across all services
	docker compose logs -f

seed: ## Load vector store corpus via a one-off backend container
	docker compose up -d qdrant
	docker compose run --rm --no-deps backend python -m data.ingest
	@echo "Reminder: Umaku workspace seeding is manual — see scripts/seed_umaku.md"

# --- Testing --------------------------------------------------------------------
# All run via one-off containers built from the same backend image —
# no local Python needed. test-integration/test-e2e need real services
# up first (`make run`), since they're not fully mocked like test-unit.

test: ## Run full test suite inside a backend container
	docker compose run --rm --no-deps backend python -m pytest tests/

test-unit: ## Fast, fully mocked — no other services need to be running
	docker compose run --rm --no-deps backend python -m pytest tests/unit

test-integration: ## Requires supporting services up (make run first)
	docker compose run --rm backend python -m pytest tests/integration

test-e2e: ## Requires the full stack up, exercises each demo moment as a real request
	docker compose run --rm backend python -m pytest tests/e2e

lint: ## Run the backend linter inside Docker; frontend linter needs local Node
	docker compose run --rm --no-deps backend python -m ruff check .
	docker compose run --rm --no-deps backend python -m ruff format --check .
	cd frontend && npm run lint

# --- Local dev iteration (NOT part of the Docker-only path above) ---------------

install: ## Create a local venv + install deps — ONLY needed for `run-local` below
	python3 -m venv backend/.venv
	backend/.venv/bin/python3 -m pip install --upgrade pip
	backend/.venv/bin/python3 -m pip install -r backend/requirements.txt
	cd frontend && npm install

run-local: ## Run backend + frontend on the HOST for faster iteration (run `make install` first)
	docker compose up -d qdrant ollama litellm otel-collector phoenix
	cd backend && .venv/bin/python3 -m uvicorn main:app --reload --port 8000 &
	cd frontend && npm run dev

# --- Demo-specific ----------------------------------------------------------------

kill-provider: ## Simulate Moment 4 — stop the primary model provider
	./scripts/kill_provider.sh

restore-provider: ## Reverse of kill-provider, restore normal operation between dry runs
	./scripts/restore_provider.sh

dry-run: start ## Convenience target: start everything + remind to open the trace dashboard
	@echo "Dry run ready."
	@echo "Langfuse:  http://localhost:3000"
	@echo "Phoenix:   http://localhost:6006"
	@echo "Frontend:  http://localhost:5173"
	@echo "Run through docs/demo_runbook.md moment by moment."
