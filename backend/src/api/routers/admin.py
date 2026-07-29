"""Admin router — gateway toggles (used by Moment 1's UI controls) and
basic health checks."""
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas.scenario import GatewayToggleRequest
from src.config.container import Container
from src.domain.interfaces.gateway import GatewayInterface
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.post(
    "/gateway/cache",
)
@inject
async def toggle_cache(
    payload: GatewayToggleRequest,
    gateway: GatewayInterface = Depends(Provide[Container.gateway]),
) -> dict:
    """Enable or disable the gateway's response cache.

    Used by the UI's cache on/off toggle in Moment 1.

    Args:
        payload: Whether caching should be enabled.
        gateway: Injected gateway.

    Returns:
        The new cache_enabled state.

    Raises:
        HTTPException: 500 if the toggle fails unexpectedly.
    """
    try:
        await gateway.set_cache_enabled(payload.enabled)
        return {"cache_enabled": payload.enabled}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to toggle cache: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Failed to toggle gateway cache.",
        )


@router.post(
    "/gateway/routing",
)
@inject
async def toggle_routing(
    payload: GatewayToggleRequest,
    gateway: GatewayInterface = Depends(Provide[Container.gateway]),
) -> dict:
    """Enable or disable the gateway's model-routing rules.

    Used by the UI's routing on/off toggle in Moment 1.

    Args:
        payload: Whether routing should be enabled.
        gateway: Injected gateway.

    Returns:
        The new routing_enabled state.

    Raises:
        HTTPException: 500 if the toggle fails unexpectedly.
    """
    try:
        await gateway.set_routing_enabled(payload.enabled)
        return {"routing_enabled": payload.enabled}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to toggle routing: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Failed to toggle gateway routing.",
        )


@router.get(
    "/gateway/status",
)
@inject
async def gateway_status(
    gateway: GatewayInterface = Depends(Provide[Container.gateway]),
) -> dict:
    """Return the gateway's current cache/routing/failover state.

    Args:
        gateway: Injected gateway.

    Returns:
        The current gateway status dict.

    Raises:
        HTTPException: 500 if the status check fails unexpectedly.
    """
    try:
        return await gateway.get_status()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to get gateway status: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get gateway status.",
        )


@router.get(
    "/health",
)
async def health() -> dict:
    """Basic liveness check.

    Does not verify downstream services (Qdrant, LiteLLM, Umaku, etc.) —
    for that, use each service's own health check or the gateway status
    endpoint above.
    """
    return {"status": "ok"}
