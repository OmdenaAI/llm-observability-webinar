"""LLM provider that routes all calls through the LiteLLM gateway.

This is the provider used in the live demo. It reads cache/routing
state from a shared LiteLLMGateway instance (see that class's docstring
for why cache/routing are implemented there rather than via a LiteLLM
admin API) and calls the gateway's OpenAI-compatible endpoint.

Routing policy (Moment 1): when routing is disabled, requests default
to "fallback-model-openai" as a deliberately non-free baseline "before"
model, so there's a real cost to optimize away. When routing is
enabled, requests are sent to "primary-model" (local Ollama, $0 cost)
instead. This is our own demo-specific routing policy, not a LiteLLM
router feature — LiteLLM's own `router_settings.routing_strategy` in
infra/litellm-config.yaml applies to load-balancing between multiple
deployments of the *same* model_name, which doesn't fit this demo's
three distinctly-named models (used for the Moment 4 fallback chain
instead).

Failover (Moment 4) is real and NOT implemented here — it's LiteLLM's
own configured `fallbacks` chain (infra/litellm-config.yaml) kicking in
server-side when the requested model is unreachable. This class detects
that it happened by comparing the model it requested to the model
LiteLLM's response reports actually served the request.
"""
import hashlib
import time

import httpx

from src.domain.entities.generation import GenerationResult
from src.infrastructure.gateway.litellm_gateway import LiteLLMGateway
from src.infrastructure.llm.base import BaseLLMProvider
from utils.logger import get_logger

logger = get_logger()

# The model requested when routing is OFF — a real hosted model, so
# there's an actual, visible cost to save once routing is enabled.
_ROUTING_DISABLED_MODEL = "fallback-model-openai"
# The model requested when routing is ON — local, $0 cost.
_ROUTING_ENABLED_MODEL = "primary-model"


def _cache_key(
    prompt: str,
    model: str,
) -> str:
    """Build a stable cache key for a given prompt and target model.

    Args:
        prompt: The fully assembled prompt string.
        model: The target model name.

    Returns:
        A hex digest suitable for use as a dict key.
    """
    return hashlib.sha256(f"{model}:{prompt}".encode("utf-8")).hexdigest()


class LiteLLMGatewayProvider(BaseLLMProvider):
    """LLM provider that calls the LiteLLM gateway's chat completions endpoint."""

    def __init__(
        self,
        gateway_url: str,
        default_model: str = "primary-model",
        gateway: LiteLLMGateway | None = None,
        admin_api_key: str = "",
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> None:
        """Initialize the provider's HTTP client and shared gateway reference.

        Args:
            gateway_url: The base URL of the LiteLLM gateway.
            default_model: The model requested when the caller passes no
                explicit model and gateway routing state can't be
                consulted (e.g. gateway is None).
            gateway: The shared LiteLLMGateway instance holding
                cache/routing state — the same instance bound to
                GatewayInterface in the DI container, so toggles made
                via the admin endpoints are visible here immediately.
            admin_api_key: LiteLLM's configured master key
                (LITELLM_ADMIN_API_KEY). Required — confirmed via a live
                run that LiteLLM's proxy rejects every route, including
                /health, with a 401 once general_settings.master_key is
                set (which infra/litellm-config.yaml does), so every
                request from this client must carry it as a Bearer token.
            temperature: Sampling temperature sent on every generation
                call. Defaults to 0.0 (deterministic) — see
                settings.generation_temperature for why: without this,
                the small local primary model produces a genuinely
                different answer on each call, which flips Moments 2/3's
                eval scores (faithfulness) run to run even though the
                judge itself is already deterministic.
            seed: Optional fixed sampling seed sent on every generation
                call, for full run-to-run reproducibility alongside
                temperature=0. None omits the parameter entirely.
        """
        self._gateway_url = gateway_url
        self._default_model = default_model
        self._gateway = gateway
        self._temperature = temperature
        self._seed = seed
        self._http_client = httpx.AsyncClient(
            base_url=gateway_url,
            timeout=30.0,
            headers={"Authorization": f"Bearer {admin_api_key}"} if admin_api_key else {},
        )

    def _pick_model(
        self,
        requested_model: str | None,
    ) -> str:
        """Choose which model to request, honoring an explicit override
        first, then the demo's routing policy.

        Args:
            requested_model: An explicit model name from the caller, if
                any.
        """
        if requested_model:
            return requested_model
        if self._gateway is not None and self._gateway.is_routing_enabled():
            return _ROUTING_ENABLED_MODEL
        if self._gateway is not None:
            return _ROUTING_DISABLED_MODEL
        return self._default_model

    async def _call_model(
        self,
        prompt: str,
        model: str | None,
    ) -> GenerationResult:
        """Call the LiteLLM gateway's chat completions endpoint.

        Checks the gateway's cache first if caching is enabled, and
        populates it after a successful call.

        Args:
            prompt: The fully assembled prompt string.
            model: An optional specific model to request; if not given,
                the gateway's routing state decides (see _pick_model).
        """
        target_model = self._pick_model(model)
        cache_key = _cache_key(prompt, target_model)

        if self._gateway is not None and self._gateway.is_cache_enabled():
            cached = self._gateway.get_cached_response(cache_key)
            if cached is not None:
                logger.debug(f"Gateway cache hit for model={target_model}")
                return GenerationResult(
                    answer=cached.answer,
                    model_used=cached.model_used,
                    prompt_tokens=cached.prompt_tokens,
                    completion_tokens=cached.completion_tokens,
                    # A cache hit costs nothing to serve — this is the
                    # entire point of Moment 1's before/after comparison.
                    cost_usd=0.0,
                    latency_ms=cached.latency_ms,
                    cache_hit=True,
                    metadata=cached.metadata,
                )

        request_body = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self._temperature,
        }
        if self._seed is not None:
            # Omitted entirely rather than sent as null — some providers
            # in the fallback chain (OpenAI/Anthropic via LiteLLM) may
            # not honor seed identically to Ollama; leaving it unset
            # when None avoids sending a meaningless seed=None downstream.
            request_body["seed"] = self._seed

        start = time.perf_counter()
        response = await self._http_client.post(
            "/chat/completions",
            json=request_body,
        )
        response.raise_for_status()
        data = response.json()
        latency_ms = (time.perf_counter() - start) * 1000

        choice = data["choices"][0]
        usage = data.get("usage", {})
        # Confirmed via LiteLLM's own issue tracker: calling the PROXY over
        # raw HTTP exposes cost via the `x-litellm-response-cost` response
        # HEADER, not a `_hidden_params` key in the JSON body (that field
        # only exists when using LiteLLM's Python SDK directly, not when
        # calling the proxy's HTTP API as we do here). Reading it from the
        # body previously always silently fell back to 0.0.
        cost_header = response.headers.get("x-litellm-response-cost")
        cost_usd = float(cost_header) if cost_header else 0.0
        model_used = data.get("model", target_model)

        # A returned model different from what we requested means
        # LiteLLM's own configured fallback chain kicked in — this is
        # exactly what ReliabilityScenario checks for in Moment 4.
        failover_triggered = model_used != target_model

        result = GenerationResult(
            answer=choice["message"]["content"],
            model_used=model_used,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            cache_hit=False,
            metadata={
                "failover_triggered": failover_triggered,
                "requested_model": target_model,
            },
        )

        if self._gateway is not None and self._gateway.is_cache_enabled():
            self._gateway.store_cached_response(cache_key, result)

        return result

    async def health_check(
        self,
    ) -> bool:
        """Return True if the LiteLLM gateway is reachable."""
        try:
            response = await self._http_client.get("/health")
            return response.status_code == 200
        except Exception as exc:  # noqa: BLE001
            logger.error(f"LiteLLM health check failed: {exc}")
            return False
