"""Entrypoint for the backend API.

Lives outside src/ so the DI container's wiring step (which needs to
know which modules use @inject) has a clear, single place to be
configured, and so `python main.py` / `uvicorn main:app` works from the
backend/ root without needing src/ on the path in a special way.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import admin, chat, scenarios
from src.config.container import Container
from src.config.settings import get_settings
from utils.logger import get_logger

logger = get_logger()


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """Manage application startup/shutdown logging.

    Args:
        app: The FastAPI application instance.
    """
    logger.info("Starting up — wiring DI container")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    """Construct and fully configure the FastAPI application.

    Wires the DI container into the router modules that use `@inject`,
    registers CORS middleware based on settings, and includes all
    routers.

    Returns:
        The fully configured FastAPI application instance.
    """
    settings = get_settings()

    container = Container()
    container.wire(
        modules=[chat, scenarios, admin],
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.container = container  # type: ignore[attr-defined]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router)
    app.include_router(scenarios.router)
    app.include_router(admin.router)

    return app


app = create_app()
