"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import CorrelationIdMiddleware, install_error_handlers
from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.services.async_runs import LocalRunDispatcher

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    dispatcher = getattr(application.state, "run_dispatcher", None)
    if dispatcher is None:
        dispatcher = LocalRunDispatcher(
            session_factory=SessionLocal,
            settings=settings,
        )
        application.state.run_dispatcher = dispatcher
    await dispatcher.start()
    logger.info(
        "application_started",
        extra={
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "qwen_configured": settings.qwen_configured,
        },
    )
    try:
        yield
    finally:
        await dispatcher.stop()
        logger.info("application_stopped", extra={"service": settings.app_name})


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Commercial opportunity automation for Galician wineries.",
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api/v1")
app.include_router(health_router)
app.add_middleware(CorrelationIdMiddleware)
install_error_handlers(app)
