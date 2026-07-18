"""Versioned product API router."""

from fastapi import APIRouter

from app.api.v1.product import router as product_router

api_router = APIRouter()
api_router.include_router(product_router)
