#!/usr/bin/env bash
# Reverses kill_provider.sh — restarts the Ollama container so subsequent
# dry runs (or a re-run of Moment 4) start from a healthy state.
#
# Usage: ./scripts/restore_provider.sh

set -euo pipefail

echo "Restarting primary model provider (ollama)..."
docker compose start ollama

echo "Waiting for Ollama to become healthy..."
sleep 5
echo "Done. Confirm with: curl http://localhost:11434/api/tags"
