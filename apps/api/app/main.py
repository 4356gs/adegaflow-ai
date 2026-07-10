"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "application_started",
        extra={
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "qwen_configured": settings.qwen_configured,
        },
    )
    yield
    logger.info("application_stopped", extra={"service": settings.app_name})


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Commercial opportunity automation for Galician wineries.",
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api/v1")

# Unversioned endpoint for container health checks.
app.include_router(api_router)
