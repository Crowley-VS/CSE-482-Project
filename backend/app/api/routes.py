"""API routes for the application."""
from fastapi import APIRouter

from app.api.endpoints import collection, events, health

router = APIRouter()

# Include endpoint routers
router.include_router(health.router, tags=["health"])
router.include_router(collection.router, prefix="/collection", tags=["collection"])
router.include_router(events.router, prefix="/events", tags=["events"])
