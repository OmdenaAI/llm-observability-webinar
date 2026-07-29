"""Abstract base for gateway implementations."""
from abc import abstractmethod

from src.domain.interfaces.gateway import GatewayInterface
from utils.logger import get_logger

logger = get_logger()


class BaseGateway(GatewayInterface):
    """Shared logging around concrete gateway control calls."""

    async def set_cache_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Log and delegate to the concrete gateway's cache toggle.

        Args:
            enabled: Whether caching should be turned on.
        """
        logger.info(f"Setting gateway cache_enabled={enabled}")
        await self._do_set_cache_enabled(enabled)

    async def set_routing_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Log and delegate to the concrete gateway's routing toggle.

        Args:
            enabled: Whether routing should be turned on.
        """
        logger.info(f"Setting gateway routing_enabled={enabled}")
        await self._do_set_routing_enabled(enabled)

    @abstractmethod
    async def _do_set_cache_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Perform the actual cache toggle against the concrete gateway.

        Args:
            enabled: Whether caching should be turned on.
        """
        raise NotImplementedError

    @abstractmethod
    async def _do_set_routing_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Perform the actual routing toggle against the concrete gateway.

        Args:
            enabled: Whether routing should be turned on.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_status(
        self,
    ) -> dict:
        """Return current cache/routing/failover state."""
        raise NotImplementedError

    @abstractmethod
    async def simulate_provider_failure(
        self,
        provider_name: str,
    ) -> None:
        """Mark a provider as failed.

        Args:
            provider_name: The name of the provider to mark as failed.
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
