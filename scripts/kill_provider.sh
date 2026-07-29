#!/usr/bin/env bash
# Simulates Moment 4's live provider outage by stopping the Ollama container
# that LiteLLM's "primary-model" points at. LiteLLM's fallback chain
# (see infra/litellm-config.yaml) should route to "fallback-model" instead.
#
# Usage: ./scripts/kill_provider.sh
# Reverse with: ./scripts/restore_provider.sh (or `make restore-provider`)

set -euo pipefail

echo "Killing primary model provider (ollama) to simulate an outage..."
docker compose stop ollama

echo "Provider stopped. LiteLLM should now be failing over to fallback-model."
echo "Watch the Langfuse/Phoenix dashboard for the circuit breaker trip."
