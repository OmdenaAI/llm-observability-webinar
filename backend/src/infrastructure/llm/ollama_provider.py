"""Direct Ollama provider — used when bypassing the gateway entirely
(e.g. local dev iteration before the gateway is wired in, or if
LLM_PROVIDER=ollama is set instead of the default "litellm").

Calls Ollama's native /api/chat endpoint directly. No caching, routing,
or cost tracking here — those are gateway-layer concerns (see
LiteLLMGatewayProvider); this class exists for the simpler no-gateway
path.
"""
import time

import httpx

from src.domain.entities.generation import GenerationResult
from src.infrastructure.llm.base import BaseLLMProvider
from utils.logger import get_logger

logger = get_logger()


class OllamaProvider(BaseLLMProvider):
    """LLM provider that calls a local Ollama instance directly."""

    def __init__(
        self,
        base_url: str,
        default_model: str = "llama3.2:1b",
    ) -> None:
        """Initialize the provider's HTTP client.

        Args:
            base_url: The base URL of the Ollama instance.
            default_model: The model to use if none is specified per call.
        """
        self._base_url = base_url
        self._default_model = default_model
        self._http_client = httpx.AsyncClient(
            base_url=base_url,
            timeout=60.0,  # local model inference can be slow on CPU
        )

    async def _call_model(
        self,
        prompt: str,
        model: str | None,
    ) -> GenerationResult:
        """Call Ollama's /api/chat endpoint with the given prompt.

        Args:
            prompt: The fully assembled prompt string.
            model: An optional specific model to use; falls back to
                `self._default_model` if not given.
        """
        target_model = model or self._default_model
        start = time.perf_counter()

        response = await self._http_client.post(
            "/api/chat",
            json={
                "model": target_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()
        latency_ms = (time.perf_counter() - start) * 1000

        # Ollama's response includes token counts under these keys when
        # available; not every model/version reports them, so default to 0.
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        return GenerationResult(
            answer=data["message"]["content"],
            model_used=target_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            # Ollama runs locally — there is no per-token cost to report.
            cost_usd=0.0,
            latency_ms=latency_ms,
            cache_hit=False,
            metadata={"requested_model": target_model},
        )

    async def health_check(
        self,
    ) -> bool:
        """Return True if the Ollama instance is reachable."""
        try:
            response = await self._http_client.get("/api/tags")
            return response.status_code == 200
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Ollama health check failed: {exc}")
            return False
