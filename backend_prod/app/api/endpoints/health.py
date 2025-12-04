"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "Economic Event Detection API - Production (Read-Only)"
    }
