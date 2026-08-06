#!/bin/sh
# Sends one throwaway generation call through the real LiteLLM -> Ollama
# path, right after the stack comes up. Ollama caches model *weights*
# on disk across restarts (see the ollama_data volume in
# docker-compose.yml), but still has to load those weights into memory
# on the first inference call after the container starts — a cost that
# was showing up as an httpx.ReadTimeout during the first live demo
# generation, most often surfacing on Moment 5 (Traceability) simply
# because it tends to be the first moment in a run that reaches
# generation after other MCP-call-heavy work. This script pays that
# cost up front instead, while you're still narrating the setup.
#
# Best-effort only: failures here are logged but never block `make
# run` — a slow/failed warm-up just means the first live generation
# may be slower than usual, not that the stack failed to start.
set -u

if [ -f .env ]; then
  # shellcheck disable=SC1091
  . ./.env
fi
LITELLM_KEY="${LITELLM_ADMIN_API_KEY:-changeme-local-dev-key}"

echo "Warming up the local model (avoids a cold-start timeout during the first live generation)..."

attempts=0
until curl -sf -o /dev/null \
  -H "Authorization: Bearer ${LITELLM_KEY}" \
  http://localhost:4000/health; do
  attempts=$((attempts + 1))
  if [ "$attempts" -ge 30 ]; then
    echo "Warm-up: LiteLLM never became healthy after 60s — skipping warm-up, stack is still up."
    exit 0
  fi
  sleep 2
done

if curl -s -X POST http://localhost:4000/chat/completions \
  -H "Authorization: Bearer ${LITELLM_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "primary-model", "messages": [{"role": "user", "content": "Say OK."}], "temperature": 0, "max_tokens": 5}' \
  -o /dev/null; then
  echo "Model warm-up complete."
else
  echo "Warm-up call failed — skipping, stack is still up. First live generation may be slower than usual."
fi