"""API routes for the application."""
from fastapi import APIRouter

from app.api.endpoints import health, events, posts, data_transfer

router = APIRouter()

# Include endpoint routers
router.include_router(health.router, tags=["health"])
router.include_router(events.router, prefix="/events", tags=["events"])
router.include_router(posts.router, prefix="/posts", tags=["posts"])
router.include_router(data_transfer.router, prefix="/data", tags=["data"])
