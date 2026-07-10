"""Health endpoint."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Public health response without secret configuration."""

    status: Literal["ok"] = "ok"
    service: str
    version: str
    environment: str
    qwen_configured: bool


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        qwen_configured=settings.qwen_configured,
    )
