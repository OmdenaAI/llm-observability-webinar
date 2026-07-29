"""Gateway implementation controlling cache/routing/failover for Moments 1 and 4.

Cache and routing state are implemented here in Python, not via a
LiteLLM admin API — LiteLLM's proxy does not expose a simple, stable
public endpoint for toggling cache/routing at runtime (its cache and
router config are primarily config-file/DB driven, confirmed while
implementing this). Implementing that control layer ourselves gives the
demo an instant, reliable toggle that doesn't depend on an uncertain
admin surface, while still using LiteLLM itself for what it's actually
well-documented for: unifying multiple providers behind one API and
running its own configured fallback chain (infra/litellm-config.yaml)
on failure — that real mechanism is what Moment 4 demonstrates.

Provider failure/restore is simulated by stopping/starting the relevant
docker-compose service directly, mirroring scripts/kill_provider.sh.
"""
import subprocess

from src.domain.entities.generation import GenerationResult
from src.infrastructure.gateway.base import BaseGateway
from utils.logger import get_logger

logger = get_logger()

# Maps a LiteLLM model_name (see infra/litellm-config.yaml) to the
# docker-compose service that must be stopped to simulate its failure.
# Only "primary-model" (local Ollama) is mapped — the fallback models
# are real hosted providers (OpenAI/Anthropic) and aren't something a
# demo can "stop" on command.
_PROVIDER_TO_COMPOSE_SERVICE = {
    "primary-model": "ollama",
}


class LiteLLMGateway(BaseGateway):
    """Gateway holding cache/routing state, plus provider failure simulation.

    Cache/routing state is read directly by LiteLLMGatewayProvider (via
    the non-interface helper methods below) — both classes are wired to
    the same singleton instance in the DI container so they share state.
    """

    def __init__(
        self,
        gateway_url: str,
        admin_api_key: str | None = None,
    ) -> None:
        """Initialize the gateway's connection parameters and control state.

        Args:
            gateway_url: The base URL of the LiteLLM gateway.
            admin_api_key: Reserved for future use if LiteLLM's admin
                surface is used directly; not currently required since
                cache/routing are implemented in this class instead.
        """
        self._gateway_url = gateway_url
        self._admin_api_key = admin_api_key
        self._cache_enabled = False
        self._routing_enabled = False
        self._response_cache: dict[str, GenerationResult] = {}

    async def _do_set_cache_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Flip the in-memory cache-enabled flag.

        Args:
            enabled: Whether caching should be turned on.
        """
        self._cache_enabled = enabled

    async def _do_set_routing_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Flip the in-memory routing-enabled flag.

        Args:
            enabled: Whether routing should be turned on.
        """
        self._routing_enabled = enabled

    async def get_status(
        self,
    ) -> dict:
        """Return current cache/routing state and cache size."""
        return {
            "cache_enabled": self._cache_enabled,
            "routing_enabled": self._routing_enabled,
            "cached_entries": len(self._response_cache),
        }

    async def simulate_provider_failure(
        self,
        provider_name: str,
    ) -> None:
        """Stop the docker-compose service backing the given provider.

        Args:
            provider_name: The LiteLLM model_name to fail (e.g.
                "primary-model").

        Raises:
            ValueError: If no compose service is mapped for the given
                provider name.
        """
        service = _PROVIDER_TO_COMPOSE_SERVICE.get(provider_name)
        if not service:
            raise ValueError(
                f"No docker-compose service mapped for provider "
                f"'{provider_name}'"
            )
        logger.info(
            f"Stopping docker-compose service '{service}' to simulate a "
            f"failure of '{provider_name}'"
        )
        subprocess.run(
            ["docker", "compose", "stop", service],
            check=True,
        )

    async def restore_provider(
        self,
        provider_name: str,
    ) -> None:
        """Start the docker-compose service backing the given provider.

        Args:
            provider_name: The LiteLLM model_name to restore.

        Raises:
            ValueError: If no compose service is mapped for the given
                provider name.
        """
        service = _PROVIDER_TO_COMPOSE_SERVICE.get(provider_name)
        if not service:
            raise ValueError(
                f"No docker-compose service mapped for provider "
                f"'{provider_name}'"
            )
        logger.info(
            f"Starting docker-compose service '{service}' to restore "
            f"'{provider_name}'"
        )
        subprocess.run(
            ["docker", "compose", "start", service],
            check=True,
        )

    # --- Non-interface helpers, used only by LiteLLMGatewayProvider ---------

    def is_cache_enabled(
        self,
    ) -> bool:
        """Return whether caching is currently enabled."""
        return self._cache_enabled

    def is_routing_enabled(
        self,
    ) -> bool:
        """Return whether routing is currently enabled."""
        return self._routing_enabled

    def get_cached_response(
        self,
        cache_key: str,
    ) -> GenerationResult | None:
        """Look up a cached response by key, if one exists.

        Args:
            cache_key: The cache key to look up.
        """
        return self._response_cache.get(cache_key)

    def store_cached_response(
        self,
        cache_key: str,
        result: GenerationResult,
    ) -> None:
        """Store a response under the given cache key.

        Args:
            cache_key: The cache key to store under.
            result: The generation result to cache.
        """
        self._response_cache[cache_key] = result
