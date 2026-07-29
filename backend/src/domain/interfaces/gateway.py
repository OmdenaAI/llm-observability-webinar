"""Contract for the LLM gateway (routing, caching, failover).

Separate from LLMProviderInterface: the gateway is a control-plane
concern (Moment 1 cost toggles, Moment 4 failover), while
LLMProviderInterface is the generation call itself. The
litellm_gateway_provider implementation typically implements both.
"""
from abc import ABC, abstractmethod


class GatewayInterface(ABC):
    """Abstract contract for controlling gateway-level behavior."""

    @abstractmethod
    async def set_cache_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Enable or disable the gateway's response cache.

        Args:
            enabled: Whether caching should be turned on.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_routing_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Enable or disable the gateway's model-routing rules.

        Args:
            enabled: Whether routing should be turned on.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_status(
        self,
    ) -> dict:
        """Return current cache/routing/failover state.

        Used by the UI toggles to reflect real gateway state.
        """
        raise NotImplementedError

    @abstractmethod
    async def simulate_provider_failure(
        self,
        provider_name: str,
    ) -> None:
        """Mark a provider as failed, used to trigger Moment 4 on demand.

        Args:
            provider_name: The name of the provider to mark as failed
                (e.g. "primary-model").
        """
        raise NotImplementedError

    @abstractmethod
    async def restore_provider(
        self,
        provider_name: str,
    ) -> None:
        """Reverse simulate_provider_failure for the given provider.

        Args:
            provider_name: The name of the provider to restore.
        """
        raise NotImplementedError
