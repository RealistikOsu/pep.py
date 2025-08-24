from __future__ import annotations

from fastapi import APIRouter

from . import api
from . import main


def create_router() -> APIRouter:
    """Create the main router with all sub-routers."""
    router = APIRouter()

    # Include main router
    router.include_router(main.router)

    # Include API router with prefix
    router.include_router(api.router, prefix="/api")

    return router


__all__ = ["api", "main", "create_router"]
